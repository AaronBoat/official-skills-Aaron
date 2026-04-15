#!/usr/bin/env python3
"""
Content Generator for Creator Insights
Uses OpenRouter to analyze viral patterns and draft optimized tweets.
"""

import argparse
import sys
import json
import os
import requests
import yaml
from typing import Dict, List, Optional
from pathlib import Path
from api_client import APIClient
from ascii_formatter import (
    create_header, create_section_header, create_ranking_list,
    create_info_panel, format_number, colorize, Colors
)


def load_config() -> Dict:
    """Load config from config.yaml if it exists, otherwise return defaults."""
    config_paths = [
        Path(__file__).parent.parent / "config.yaml",
        Path(__file__).parent.parent / "config.example.yaml",
    ]
    for path in config_paths:
        if path.exists():
            try:
                with open(path) as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
    return {}


def _is_original_tweet(tweet: Dict) -> bool:
    """
    Check if a tweet is original content (not RT, not reply).
    Uses text-based detection since the API's is_retweet flag is unreliable.
    """
    if tweet.get("is_retweet"):
        return False
    if tweet.get("is_reply"):
        return False
    if tweet.get("text", "").startswith("RT @"):
        return False
    return True


def _is_branded_account(user: Dict) -> bool:
    """
    Detect if a user account is a brand/corporate account vs an organic creator.

    Uses multiple signals:
    1. verifiedType == "Business" from Twitter API (strongest signal)
    2. Username/name heuristics (Official, HQ, Exchange, Protocol, etc.)
    3. Bio heuristics (corporate language patterns)

    Args:
        user: User dict with fields from _parse_user_object or author embed.
              Accepts both formats (verified_type or verifiedType).

    Returns:
        True if likely a branded/corporate account
    """
    # Signal 1: Twitter's own business verification
    verified_type = user.get("verified_type") or user.get("verifiedType")
    if verified_type == "Business":
        return True

    username = (user.get("username") or user.get("userName") or "").lower()
    name = (user.get("name") or "").lower()
    bio = (user.get("description") or user.get("bio") or "").lower()

    # Signal 2: Username/name patterns
    brand_username_markers = [
        "official", "_hq", "hq_", "markets", "exchange", "protocol",
        "network", "finance", "labs", "foundation", "ventures", "capital",
        "global", "media", "news", "daily", "alert", "signals",
    ]
    for marker in brand_username_markers:
        if marker in username or marker in name:
            return True

    # Signal 3: Bio patterns
    brand_bio_patterns = [
        "official account", "official twitter",
        "leading exchange", "leading platform", "leading provider",
        "crypto exchange", "trading platform",
        "join us", "sign up", "download now",
        "million+ users", "million+ traders", "m+ users", "m+ traders",
        "customer support", "help desk",
        "powered by", "built by", "backed by",
    ]
    for pattern in brand_bio_patterns:
        if pattern in bio:
            return True

    return False


def _extract_style_profile(tweets: List[Dict], username: str) -> Dict:
    """
    Build a detailed style profile from a user's original tweets.

    Analyzes: length, punctuation, emoji usage, hashtag usage,
    capitalization, sentence structure, tone markers, and vocabulary.

    Returns a dict with style attributes and sample tweets.
    """
    originals = [t for t in tweets if _is_original_tweet(t)]

    if not originals:
        return {"error": "No original tweets found", "samples": []}

    texts = [t["text"] for t in originals]

    # Length analysis
    lengths = [len(t) for t in texts]
    avg_len = sum(lengths) / len(lengths)
    short_count = sum(1 for l in lengths if l < 80)
    long_count = sum(1 for l in lengths if l > 200)

    if avg_len < 80:
        length_style = "very short and punchy"
    elif avg_len < 140:
        length_style = "concise"
    elif avg_len < 220:
        length_style = "medium-length"
    else:
        length_style = "long-form"

    # Emoji analysis
    emoji_count = 0
    for text in texts:
        emoji_count += sum(1 for c in text if ord(c) > 0x1F300)
    emoji_per_tweet = emoji_count / len(texts)

    if emoji_per_tweet < 0.1:
        emoji_style = "never uses emojis"
    elif emoji_per_tweet < 0.5:
        emoji_style = "rarely uses emojis"
    elif emoji_per_tweet < 2:
        emoji_style = "occasionally uses emojis"
    else:
        emoji_style = "frequently uses emojis"

    # Hashtag analysis
    hashtag_tweets = sum(1 for t in originals if t.get("hashtags"))
    hashtag_pct = hashtag_tweets / len(originals) * 100

    if hashtag_pct < 5:
        hashtag_style = "never uses hashtags"
    elif hashtag_pct < 20:
        hashtag_style = "rarely uses hashtags"
    else:
        hashtag_style = "regularly uses hashtags"

    # Punctuation and structure
    question_count = sum(1 for t in texts if '?' in t)
    exclamation_count = sum(1 for t in texts if '!' in t)
    ellipsis_count = sum(1 for t in texts if '...' in t)
    newline_count = sum(1 for t in texts if '\n' in t)

    # Capitalization
    allcaps_words = 0
    total_words = 0
    for text in texts:
        words = text.split()
        total_words += len(words)
        allcaps_words += sum(1 for w in words if w.isupper() and len(w) > 1)

    # Tone markers
    casual_markers = ['lol', 'lmao', 'tbh', 'ngl', 'fr', 'bruh', 'vibes']
    formal_markers = ['however', 'therefore', 'furthermore', 'regarding', 'analysis']
    opinionated_markers = ['I think', 'I believe', 'honestly', 'personally', 'imo']

    all_text_lower = " ".join(texts).lower()
    casual_score = sum(all_text_lower.count(m) for m in casual_markers)
    formal_score = sum(all_text_lower.count(m) for m in formal_markers)
    opinionated_score = sum(all_text_lower.count(m) for m in opinionated_markers)

    if casual_score > formal_score * 2:
        tone = "casual and conversational"
    elif formal_score > casual_score * 2:
        tone = "formal and analytical"
    elif opinionated_score > 3:
        tone = "opinionated and direct"
    else:
        tone = "balanced and natural"

    # Build style summary
    style_rules = []
    style_rules.append(f"Tweet length: {length_style} (avg {avg_len:.0f} chars)")
    style_rules.append(f"Emojis: {emoji_style}")
    style_rules.append(f"Hashtags: {hashtag_style}")
    style_rules.append(f"Tone: {tone}")

    if question_count / len(texts) > 0.3:
        style_rules.append("Often asks questions")
    if newline_count / len(texts) > 0.3:
        style_rules.append("Uses line breaks for emphasis")
    if ellipsis_count / len(texts) > 0.2:
        style_rules.append("Uses ellipsis (...) for trailing thoughts")
    if short_count / len(texts) > 0.5:
        style_rules.append("Frequently posts one-liners")

    # Pick best sample tweets (highest engagement, original only)
    scored = []
    for t in originals:
        eng = t["likes"] + t["retweets"] + t["replies"]
        scored.append((eng, t["text"]))
    scored.sort(reverse=True)

    # Take top 5 by engagement + 3 random for variety
    best = [text for _, text in scored[:5]]
    rest = [text for _, text in scored[5:] if len(text) > 20]
    import random
    samples = best + (random.sample(rest, min(3, len(rest))) if rest else [])

    return {
        "username": username,
        "original_tweet_count": len(originals),
        "total_tweet_count": len(tweets),
        "avg_length": avg_len,
        "length_style": length_style,
        "emoji_style": emoji_style,
        "hashtag_style": hashtag_style,
        "tone": tone,
        "style_rules": style_rules,
        "samples": samples
    }


class ContentGenerator:
    """AI-powered content generation using OpenRouter via sc-proxy"""

    def __init__(self, api_client: APIClient, openrouter_key: Optional[str] = None,
                 config: Optional[Dict] = None):
        self.api_client = api_client
        self.openrouter_key = openrouter_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.config = config or load_config()

        # Read model settings from config
        or_config = self.config.get("openrouter", {})
        self.default_model = or_config.get("default_model", "openai/gpt-4o-mini")
        self.default_temperature = or_config.get("temperature", 0.7)
        self.default_max_tokens = or_config.get("max_tokens", 2000)

    def _call_openrouter(self, messages: List[Dict], model: Optional[str] = None,
                        max_tokens: Optional[int] = None) -> Optional[str]:
        """
        Call OpenRouter API with messages via sc-proxy.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: from config)
            max_tokens: Maximum tokens to generate (default: from config)

        Returns:
            Generated text response
        """
        if not self.openrouter_key:
            print("OpenRouter API key not configured", file=sys.stderr)
            print("Set OPENROUTER_API_KEY environment variable", file=sys.stderr)
            return None

        model = model or self.default_model
        max_tokens = max_tokens or self.default_max_tokens

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/creator-insights",
            "X-Title": "Creator Insights Tool"
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.default_temperature
        }

        try:
            # Configure proxy if available (for routing through sc-proxy)
            proxies = None
            proxy_host = os.environ.get("PROXY_HOST")
            proxy_port = os.environ.get("PROXY_PORT")
            if proxy_host and proxy_port:
                if ':' in proxy_host and not proxy_host.startswith('['):
                    proxy_host = f"[{proxy_host}]"
                proxy_url = f"http://{proxy_host}:{proxy_port}"
                proxies = {"http": proxy_url, "https": proxy_url}

            response = requests.post(url, headers=headers, json=payload, proxies=proxies, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            if hasattr(e, 'response') and e.response:
                print(f"OpenRouter API error: {e}", file=sys.stderr)
                print(f"Response: {e.response.text}", file=sys.stderr)
            else:
                print(f"Error calling OpenRouter: {e}", file=sys.stderr)
            return None

    def analyze_viral_patterns(self, username: str, num_tweets: int = 50,
                              min_engagement: int = 100) -> Dict:
        """
        Analyze viral patterns in a user's tweets using AI.

        Args:
            username: Twitter username to analyze
            num_tweets: Number of recent tweets to analyze
            min_engagement: Minimum engagement threshold for viral content

        Returns:
            Dict with viral pattern analysis and insights
        """
        print(f"Analyzing viral patterns for @{username}...", file=sys.stderr)

        # Step 1: Fetch user's tweets
        tweets = self.api_client.get_twitter_user_timeline(username, num_tweets)
        if not tweets:
            return {"error": "Could not fetch tweets"}

        # Step 2: Filter for high-engagement ORIGINAL tweets only
        viral_tweets = []
        for tweet in tweets:
            if not _is_original_tweet(tweet):
                continue
            engagement = tweet["likes"] + tweet["retweets"] + tweet["replies"] + tweet.get("quotes", 0)
            if engagement >= min_engagement:
                viral_tweets.append({
                    "text": tweet["text"],
                    "engagement": engagement,
                    "likes": tweet["likes"],
                    "retweets": tweet["retweets"],
                    "replies": tweet["replies"],
                    "quotes": tweet.get("quotes", 0),
                    "created_at": tweet["created_at"],
                    "hashtags": tweet.get("hashtags", []),
                    "url": tweet.get("url", "")
                })

        if not viral_tweets:
            return {
                "username": username,
                "viral_tweets_found": 0,
                "message": f"No original tweets with {min_engagement}+ engagement found"
            }

        # Sort by engagement
        viral_tweets.sort(key=lambda x: x["engagement"], reverse=True)
        top_viral = viral_tweets[:10]

        print(f"Found {len(viral_tweets)} viral tweets. Analyzing patterns with AI...", file=sys.stderr)

        # Build style context so the AI doesn't recommend things that contradict the creator's style
        style_profile = _extract_style_profile(tweets, username)
        style_note = ""
        if style_profile.get("style_rules"):
            no_emoji = "never" in style_profile.get("emoji_style", "") or "rarely" in style_profile.get("emoji_style", "")
            no_hashtag = "never" in style_profile.get("hashtag_style", "")
            style_note = f"""

Creator's established style:
- {style_profile['length_style']} tweets (avg {style_profile['avg_length']:.0f} chars)
- {style_profile['emoji_style']}
- {style_profile['hashtag_style']}
- {style_profile['tone']} tone

IMPORTANT: Your analysis must respect this creator's style. {"They deliberately avoid hashtags — do not recommend adding hashtags." if no_hashtag else ""} {"They rarely/never use emojis — do not recommend adding emojis." if no_emoji else ""} Recommend ways to amplify what already works, not generic best practices that contradict their approach."""

        # Step 3: Use AI to analyze patterns
        analysis_prompt = f"""Analyze these top-performing tweets from @{username} and identify viral patterns.

Top Viral Tweets:
{json.dumps(top_viral[:5], indent=2)}
{style_note}

Provide a detailed analysis covering:
1. Content themes that perform best
2. Tweet structure patterns (length, format, use of questions, threads, etc.)
3. Optimal posting times (if patterns emerge from created_at timestamps)
4. Engagement patterns (what drives likes vs retweets vs replies?)
5. Key success factors and recommendations that fit this creator's voice

Format your response as a structured analysis with clear sections."""

        messages = [
            {"role": "user", "content": analysis_prompt}
        ]

        ai_analysis = self._call_openrouter(messages, max_tokens=2000)

        if not ai_analysis:
            return {"error": "Failed to generate AI analysis"}

        return {
            "username": username,
            "total_tweets_analyzed": len(tweets),
            "viral_tweets_found": len(viral_tweets),
            "engagement_threshold": min_engagement,
            "top_viral_tweets": top_viral[:10],
            "ai_analysis": ai_analysis,
            "avg_viral_engagement": sum(t["engagement"] for t in viral_tweets) / len(viral_tweets) if viral_tweets else 0
        }

    def draft_tweet_variations(self, topic: str, style_reference_username: Optional[str] = None,
                              num_variations: int = 5, max_length: int = 280) -> List[Dict]:
        """
        Draft tweet variations on a topic, matching a reference creator's voice.

        Args:
            topic: Topic or idea to tweet about
            style_reference_username: Optional username to match writing style
            num_variations: Number of variations to generate (3-5)
            max_length: Maximum tweet length (default: 280 chars)

        Returns:
            List of tweet variations with metadata
        """
        print(f"Drafting {num_variations} tweet variations on: '{topic}'", file=sys.stderr)

        # Step 1: Build detailed style profile if reference provided
        style_block = ""
        if style_reference_username:
            print(f"Analyzing writing style of @{style_reference_username}...", file=sys.stderr)
            tweets = self.api_client.get_twitter_user_timeline(style_reference_username, max_results=50)
            if tweets:
                profile = _extract_style_profile(tweets, style_reference_username)

                if profile.get("samples"):
                    # Build a strict style enforcement block
                    rules_text = "\n".join(f"- {r}" for r in profile["style_rules"])
                    samples_text = "\n".join(f'"""\n{s}\n"""' for s in profile["samples"][:8])

                    no_emoji = "never" in profile['emoji_style'] or "rarely" in profile['emoji_style']
                    no_hashtag = "never" in profile['hashtag_style']

                    style_block = f"""

VOICE CLONING — THIS OVERRIDES EVERYTHING ELSE:
You are writing AS @{style_reference_username}. Every tweet must sound like it came from their keyboard, not from an AI.

Study these real tweets from @{style_reference_username} — this is the voice you must clone:

{samples_text}

MANDATORY CONSTRAINTS (violating any of these = failure):
1. Length: {profile['length_style']} — target around {profile['avg_length']:.0f} characters. {"Most of their tweets are one-liners or 1-2 short sentences." if profile['avg_length'] < 140 else ""}
2. Emojis: {"ZERO emojis. This person does not use emojis. Do NOT add any." if no_emoji else "Match their emoji frequency."}
3. Hashtags: {"ZERO hashtags. This person never uses hashtags. Do NOT add any." if no_hashtag else "Match their hashtag usage."}
4. Tone: {profile['tone']} — match their vocabulary and sentence structure exactly.
5. No corporate language, no marketing speak, no "leverage", "optimize", "strategies", "insights".
6. No listicle formats unless they use them. No thread prompts unless they do threads.
7. If they use line breaks for emphasis, you should too. If they write in fragments, you should too."""

                    print(f"  Style profile: {profile['length_style']}, {profile['emoji_style']}, {profile['hashtag_style']}, {profile['tone']}", file=sys.stderr)
                    print(f"  Original tweets sampled: {profile['original_tweet_count']}/{profile['total_tweet_count']}", file=sys.stderr)

        # Step 2: Generate tweet variations with AI
        generation_prompt = f"""Draft {num_variations} tweets about this topic:{style_block}

Topic: {topic}

Requirements:
- Maximum {max_length} characters per tweet
- Each variation should use a different angle or hook
- Sound like a real person, not an AI or a marketer

Format your response as a JSON array with this structure:
[
  {{
    "text": "Tweet text here...",
    "strategy": "Brief explanation of the angle/hook used",
    "predicted_engagement": "high/medium description"
  }},
  ...
]

Return ONLY the JSON array, no other text."""

        messages = [
            {"role": "user", "content": generation_prompt}
        ]

        ai_response = self._call_openrouter(messages, max_tokens=2000)

        if not ai_response:
            return []

        # Step 3: Parse AI response
        try:
            json_start = ai_response.find('[')
            json_end = ai_response.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                variations = json.loads(json_str)

                for i, variation in enumerate(variations, 1):
                    variation["id"] = i
                    variation["character_count"] = len(variation["text"])
                    variation["within_limit"] = variation["character_count"] <= max_length

                return variations[:num_variations]
            else:
                print("Could not extract JSON from AI response", file=sys.stderr)
                return []
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}", file=sys.stderr)
            print(f"Response was: {ai_response[:200]}...", file=sys.stderr)
            return []

    def optimize_existing_tweet(self, tweet_text: str, optimization_goal: str = "engagement",
                               style_reference_username: Optional[str] = None) -> Dict:
        """
        Optimize an existing tweet draft for better performance.

        Args:
            tweet_text: Original tweet text
            optimization_goal: "engagement", "reach", "replies", or "clarity"
            style_reference_username: Optional username to preserve voice

        Returns:
            Dict with optimized version and explanation
        """
        print(f"Optimizing tweet for {optimization_goal}...", file=sys.stderr)

        goal_descriptions = {
            "engagement": "maximize total engagement (likes + retweets + replies)",
            "reach": "maximize viral potential and reach",
            "replies": "encourage conversation and replies",
            "clarity": "improve clarity and impact"
        }

        goal_desc = goal_descriptions.get(optimization_goal, "improve overall performance")

        # Build style context if reference provided
        style_instruction = ""
        if style_reference_username:
            print(f"Loading style from @{style_reference_username}...", file=sys.stderr)
            tweets = self.api_client.get_twitter_user_timeline(style_reference_username, max_results=50)
            if tweets:
                profile = _extract_style_profile(tweets, style_reference_username)
                if profile.get("samples"):
                    no_emoji = "never" in profile['emoji_style'] or "rarely" in profile['emoji_style']
                    no_hashtag = "never" in profile['hashtag_style']
                    samples_text = "\n".join(f'- {s}' for s in profile["samples"][:5])

                    style_instruction = f"""

VOICE CONSTRAINT — The optimized tweet must sound like @{style_reference_username}:
{samples_text}

STRICT:
- {"ZERO emojis — this person does not use emojis." if no_emoji else "Match their emoji usage."}
- {"ZERO hashtags — this person never uses hashtags." if no_hashtag else "Match their hashtag usage."}
- Tone: {profile['tone']}
- No corporate language, no marketing speak."""

        optimization_prompt = f"""Optimize this tweet to {goal_desc}.

Original Tweet:
"{tweet_text}"
{style_instruction}

Provide:
1. An optimized version (max 280 characters)
2. 2-3 alternative variations with different approaches
3. Explanation of changes made and why they improve {optimization_goal}
4. Specific tips for timing and posting strategy

RULES:
- Optimize through better wording, structure, and hooks — NOT by adding hashtags or emojis.
- Do NOT add hashtags unless one was already in the original tweet.
- Do NOT add emojis unless the original tweet already used them.
- The optimized tweet should sound like the same person wrote it, just sharper.

Format as JSON:
{{
  "optimized": "Optimized tweet text",
  "alternatives": ["Alt 1", "Alt 2", "Alt 3"],
  "explanation": "Why these changes work...",
  "posting_tips": "Best timing and strategy..."
}}

Return ONLY the JSON, no other text."""

        messages = [
            {"role": "user", "content": optimization_prompt}
        ]

        ai_response = self._call_openrouter(messages, max_tokens=1500)

        if not ai_response:
            return {"error": "Failed to optimize tweet"}

        try:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                result = json.loads(json_str)
                result["original"] = tweet_text
                result["goal"] = optimization_goal
                return result
            else:
                return {"error": "Could not extract JSON from AI response"}
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response: {e}", file=sys.stderr)
            return {"error": "Failed to parse optimization results"}


def main():
    """CLI interface for Content Generator"""
    parser = argparse.ArgumentParser(description="AI-powered content generation for Twitter")
    parser.add_argument("--action", choices=["analyze", "draft", "optimize"], required=True,
                       help="Action to perform")

    # Analyze viral patterns
    parser.add_argument("--username", help="Username for analysis or style reference")
    parser.add_argument("--tweets", type=int, default=50, help="Number of tweets to analyze")
    parser.add_argument("--min-engagement", type=int, default=100, help="Minimum engagement threshold")

    # Draft variations
    parser.add_argument("--topic", help="Topic to draft tweets about")
    parser.add_argument("--variations", type=int, default=5, help="Number of variations to generate")
    parser.add_argument("--max-length", type=int, default=280, help="Maximum tweet length")

    # Optimize existing
    parser.add_argument("--text", help="Tweet text to optimize")
    parser.add_argument("--goal", choices=["engagement", "reach", "replies", "clarity"],
                       default="engagement", help="Optimization goal")

    # Model override
    parser.add_argument("--model", help="Override OpenRouter model (e.g. anthropic/claude-sonnet-4)")

    parser.add_argument("--output", choices=['json', 'text'], default='text', help="Output format")

    args = parser.parse_args()

    # Initialize with config
    api_client = APIClient()
    config = load_config()
    generator = ContentGenerator(api_client, config=config)

    # Apply model override if provided
    if args.model:
        generator.default_model = args.model

    # Execute action
    if args.action == "analyze":
        if not args.username:
            print("Error: --username required for analyze action", file=sys.stderr)
            sys.exit(1)
        result = generator.analyze_viral_patterns(args.username, args.tweets, args.min_engagement)

    elif args.action == "draft":
        if not args.topic:
            print("Error: --topic required for draft action", file=sys.stderr)
            sys.exit(1)
        result = generator.draft_tweet_variations(args.topic, args.username, args.variations, args.max_length)

    elif args.action == "optimize":
        if not args.text:
            print("Error: --text required for optimize action", file=sys.stderr)
            sys.exit(1)
        result = generator.optimize_existing_tweet(args.text, args.goal, args.username)

    # Output results
    if args.output == 'json':
        print(json.dumps(result, indent=2))
    else:
        if isinstance(result, dict) and "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        # Format text output
        if args.action == "analyze":
            print(create_header(f"  VIRAL PATTERN ANALYSIS: @{args.username}  ", 70))

            stats = [
                f"Total Tweets Analyzed: {colorize(str(result['total_tweets_analyzed']), Colors.BRIGHT_CYAN)}",
                f"Viral Tweets Found: {colorize(str(result['viral_tweets_found']), Colors.BRIGHT_GREEN)}",
                f"Engagement Threshold: {colorize(format_number(result['engagement_threshold']), Colors.BRIGHT_YELLOW)}",
                f"Avg Viral Engagement: {colorize(format_number(int(result['avg_viral_engagement'])), Colors.BRIGHT_YELLOW)}"
            ]
            print(create_info_panel("📊", "Statistics", stats, 70))

            if result.get("top_viral_tweets"):
                print(create_section_header("🔥 TOP VIRAL TWEETS", 70))
                for i, tweet in enumerate(result["top_viral_tweets"][:5], 1):
                    rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    print(f"\n  {rank_emoji} {colorize(format_number(tweet['engagement']), Colors.BRIGHT_GREEN)} total engagement")
                    print(f"  💬 {tweet['text'][:70]}{'...' if len(tweet['text']) > 70 else ''}")
                    print(f"  📊 {tweet['likes']:,} likes | {tweet['retweets']:,} RTs | {tweet['replies']:,} replies")

            if result.get("ai_analysis"):
                print(create_section_header("🤖 AI PATTERN ANALYSIS", 70))
                print(f"\n{result['ai_analysis']}\n")

        elif args.action == "draft":
            print(create_header(f"  TWEET VARIATIONS: {args.topic[:30]}...  ", 70))

            if isinstance(result, list) and result:
                print(create_section_header(f"📝 {len(result)} GENERATED VARIATIONS", 70))

                for variation in result:
                    status = "✓" if variation.get("within_limit", True) else "⚠ TOO LONG"
                    var_id = variation["id"]
                    char_count = variation["character_count"]
                    print(f"\n  {colorize(f'Variation {var_id}', Colors.BRIGHT_CYAN)} [{status}] ({char_count}/280 chars)")
                    print(f"  ─────────────────────────────────────────────────────────")
                    print(f"  {variation['text']}")
                    print(f"\n  💡 Strategy: {variation.get('strategy', 'N/A')}")
                    print(f"  📈 Predicted: {variation.get('predicted_engagement', 'N/A')}")
            else:
                print("\n  No variations generated.\n")

        elif args.action == "optimize":
            print(create_header("  TWEET OPTIMIZATION  ", 70))

            print(f"\n  {colorize('ORIGINAL:', Colors.BRIGHT_YELLOW)}")
            print(f"  {result.get('original', '')}\n")

            print(f"  {colorize('OPTIMIZED:', Colors.BRIGHT_GREEN)}")
            print(f"  {result.get('optimized', '')}\n")

            if result.get("alternatives"):
                print(create_section_header("🔄 ALTERNATIVES", 70))
                for i, alt in enumerate(result["alternatives"], 1):
                    print(f"  {i}. {alt}")

            if result.get("explanation"):
                print(create_section_header("💡 WHY THIS WORKS", 70))
                print(f"  {result['explanation']}\n")

            if result.get("posting_tips"):
                print(create_section_header("⏰ POSTING TIPS", 70))
                print(f"  {result['posting_tips']}\n")

        print()


if __name__ == "__main__":
    main()
