#!/usr/bin/env python3
"""
Twitter Profile Analyzer for Creator Insights
Analyzes a Twitter account's posting style, niche, and content patterns.
Uses AI for granular niche detection when OpenRouter is available.
"""

import argparse
import sys
import json
import os
import re
import requests
from typing import Dict, List, Optional, Tuple
from collections import Counter
from api_client import APIClient
from content_generator import _is_original_tweet, _extract_style_profile, load_config


class ProfileAnalyzer:
    """Analyzes Twitter profiles to detect niche and content style"""

    def __init__(self, api_client: APIClient, openrouter_key: Optional[str] = None,
                 config: Optional[Dict] = None):
        self.api_client = api_client
        self.openrouter_key = openrouter_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.config = config or load_config()

        or_config = self.config.get("openrouter", {})
        self.default_model = or_config.get("default_model", "openai/gpt-4o-mini")
        self.default_temperature = or_config.get("temperature", 0.7)

    def _call_openrouter(self, messages: List[Dict], max_tokens: int = 1500) -> Optional[str]:
        """Call OpenRouter API for AI-powered analysis."""
        if not self.openrouter_key:
            return None

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/creator-insights",
            "X-Title": "Creator Insights Tool"
        }

        payload = {
            "model": self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.default_temperature
        }

        try:
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
            print(f"OpenRouter error: {e}", file=sys.stderr)
            return None

    def analyze_profile(self, profile_url: str) -> Dict:
        """
        Analyze a Twitter account to detect niche and content style.

        Uses AI for granular niche detection when OpenRouter is available,
        falls back to keyword matching otherwise.

        Args:
            profile_url: Twitter URL or username (e.g., @username or twitter.com/username)

        Returns:
            Dict with niche, themes, tone, and content preferences
        """
        username = self._parse_username(profile_url)
        if not username:
            return {"error": "Could not parse profile URL. Provide a valid URL or username."}

        print(f"Analyzing Twitter profile: @{username}", file=sys.stderr)

        # Fetch recent tweets
        tweets = self.api_client.get_twitter_user_timeline(username, max_results=50)
        if not tweets:
            return {
                "error": f"Could not fetch tweets for @{username}",
                "suggestion": "Check API configuration or provide a different profile"
            }

        # Filter to original tweets only
        originals = [t for t in tweets if _is_original_tweet(t)]
        print(f"Found {len(originals)} original tweets (filtered {len(tweets) - len(originals)} RTs)", file=sys.stderr)

        if not originals:
            return {
                "error": f"No original tweets found for @{username} (all are retweets)",
                "suggestion": "Try a different account or fetch more tweets"
            }

        # Get user profile info
        user_info = self.api_client.get_twitter_user_info(username)

        # Build style profile using shared utility
        style_profile = _extract_style_profile(tweets, username)

        # Detect niche — AI if available, keyword fallback otherwise
        if self.openrouter_key:
            print(f"Using AI for granular niche detection...", file=sys.stderr)
            niche_analysis = self._detect_niche_ai(originals, user_info)
        else:
            print(f"No OpenRouter key — using keyword-based niche detection", file=sys.stderr)
            niche_analysis = self._detect_niche_keywords(originals)

        analysis = {
            "username": username,
            "bio": user_info.get("description", "") if user_info else "",
            "niche": niche_analysis,
            "style": {
                "length": style_profile.get("length_style", "unknown"),
                "avg_chars": round(style_profile.get("avg_length", 0)),
                "emoji_usage": style_profile.get("emoji_style", "unknown"),
                "hashtag_usage": style_profile.get("hashtag_style", "unknown"),
                "tone": style_profile.get("tone", "unknown"),
                "style_rules": style_profile.get("style_rules", [])
            },
            "content_mix": self._analyze_content_mix(tweets),
            "hashtags": self._extract_common_hashtags(originals),
            "posting_pattern": self._analyze_posting_pattern(originals),
            "tweets_analyzed": {
                "total": len(tweets),
                "original": len(originals),
                "retweets": len(tweets) - len(originals)
            }
        }

        return analysis

    def _parse_username(self, profile_url: str) -> Optional[str]:
        """Extract Twitter username from URL or handle."""
        clean_url = re.sub(r'https?://(www\.)?', '', profile_url)
        twitter_pattern = r'(twitter|x)\.com/([^/?]+)'
        match = re.search(twitter_pattern, clean_url)
        if match:
            return match.group(2).strip('@')
        return profile_url.strip('@').strip()

    def _detect_niche_ai(self, originals: List[Dict], user_info: Optional[Dict]) -> Dict:
        """
        Use AI to detect granular niche from tweet content.

        Returns specific sub-niches, not broad categories.
        e.g. "Solana mobile ecosystem" not just "crypto"
        """
        # Pick the best original tweets for analysis
        scored = []
        for t in originals:
            eng = t["likes"] + t["retweets"] + t["replies"]
            scored.append((eng, t["text"]))
        scored.sort(reverse=True)
        sample_texts = [text for _, text in scored[:15]]

        bio = ""
        if user_info:
            bio = user_info.get("description", "")

        samples_block = "\n".join(f"- {t}" for t in sample_texts)

        prompt = f"""Analyze this Twitter account and identify their specific niche. Be VERY granular — don't say "crypto" when you can say "Solana ecosystem and mobile crypto hardware." Don't say "tech" when you can say "AI developer tools and LLM infrastructure."

Bio: {bio}

Recent original tweets (sorted by engagement):
{samples_block}

Return a JSON object with this exact structure:
{{
  "primary_niche": "The specific niche in 3-8 words",
  "sub_topics": ["specific sub-topic 1", "specific sub-topic 2", "specific sub-topic 3"],
  "positioning": "How they position themselves in 1 sentence (e.g. 'industry insider sharing alpha' vs 'retail trader posting charts')",
  "audience": "Who their content is for in 1 sentence",
  "content_pillars": ["pillar 1", "pillar 2", "pillar 3"],
  "differentiator": "What makes their perspective unique in 1 sentence"
}}

Be specific. Use the actual project names, technologies, and topics you see in their tweets. Return ONLY the JSON."""

        messages = [{"role": "user", "content": prompt}]
        ai_response = self._call_openrouter(messages, max_tokens=800)

        if not ai_response:
            return self._detect_niche_keywords(originals)

        try:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(ai_response[json_start:json_end])
                result["method"] = "ai"
                return result
        except json.JSONDecodeError:
            pass

        return self._detect_niche_keywords(originals)

    def _detect_niche_keywords(self, originals: List[Dict]) -> Dict:
        """Fallback keyword-based niche detection."""
        niche_keywords = {
            "fitness": ["fitness", "workout", "gym", "exercise", "health", "training", "muscle", "yoga"],
            "tech": ["tech", "technology", "coding", "programming", "software", "hardware", "gadget"],
            "ai/ml": ["ai", "machine learning", "llm", "gpt", "neural", "model", "training data"],
            "crypto/web3": ["crypto", "bitcoin", "ethereum", "solana", "defi", "nft", "web3", "token", "blockchain"],
            "gaming": ["gaming", "game", "gamer", "esports", "stream", "gameplay"],
            "beauty": ["makeup", "beauty", "skincare", "cosmetics", "tutorial", "grwm"],
            "food": ["food", "recipe", "cooking", "chef", "meal", "cuisine", "foodie"],
            "fashion": ["fashion", "style", "outfit", "ootd", "clothing", "trend"],
            "travel": ["travel", "trip", "destination", "explore", "adventure", "vacation"],
            "comedy": ["comedy", "funny", "meme", "humor", "joke", "laugh", "skit"],
            "education": ["education", "learn", "tutorial", "howto", "teaching", "lesson"],
            "business": ["business", "entrepreneur", "startup", "marketing", "sales", "finance"],
            "music": ["music", "song", "sing", "cover", "musician", "artist", "band"],
            "art": ["art", "drawing", "painting", "artist", "creative", "design", "illustration"],
        }

        all_text = " ".join(t["text"] for t in originals).lower()

        niche_scores = {}
        for niche, keywords in niche_keywords.items():
            score = sum(all_text.count(keyword) for keyword in keywords)
            niche_scores[niche] = score

        if not niche_scores or max(niche_scores.values()) == 0:
            return {
                "primary_niche": "general/lifestyle",
                "sub_topics": [],
                "method": "keywords"
            }

        top_niche = max(niche_scores, key=niche_scores.get)
        threshold = niche_scores[top_niche] * 0.5
        secondary = [n for n, s in niche_scores.items() if s > threshold and n != top_niche]

        return {
            "primary_niche": top_niche,
            "sub_topics": secondary[:3],
            "method": "keywords",
            "note": "Set OPENROUTER_API_KEY for granular AI-powered niche detection"
        }

    def _analyze_content_mix(self, tweets: List[Dict]) -> Dict:
        """Analyze the mix of original vs RT vs reply content."""
        original = 0
        retweets = 0
        replies = 0
        quotes = 0

        for t in tweets:
            if t["text"].startswith("RT @"):
                retweets += 1
            elif t.get("is_reply"):
                replies += 1
            elif t.get("is_quote"):
                quotes += 1
            else:
                original += 1

        total = len(tweets)
        return {
            "original": original,
            "retweets": retweets,
            "replies": replies,
            "quotes": quotes,
            "original_pct": round(original / total * 100, 1) if total else 0,
            "retweet_pct": round(retweets / total * 100, 1) if total else 0
        }

    def _extract_common_hashtags(self, originals: List[Dict]) -> List[str]:
        """Extract most commonly used hashtags from original tweets."""
        all_hashtags = []
        for t in originals:
            all_hashtags.extend(t.get("hashtags", []))
            text_hashtags = re.findall(r'#(\w+)', t.get("text", ""))
            all_hashtags.extend(text_hashtags)

        if not all_hashtags:
            return []

        common = Counter(all_hashtags).most_common(10)
        return [f"#{tag}" for tag, _ in common]

    def _analyze_posting_pattern(self, originals: List[Dict]) -> Dict:
        """Analyze posting frequency."""
        post_count = len(originals)

        if post_count >= 25:
            frequency = "very active (7+ posts/week)"
        elif post_count >= 15:
            frequency = "active (3-6 posts/week)"
        elif post_count >= 7:
            frequency = "moderate (1-2 posts/week)"
        else:
            frequency = "occasional (<1 post/week)"

        return {
            "frequency": frequency,
            "original_posts_sampled": post_count
        }


def main():
    """CLI interface for Twitter profile analyzer"""
    parser = argparse.ArgumentParser(description="Analyze Twitter account profile")
    parser.add_argument("--profile", "--username", required=True, dest="profile", help="Twitter username or URL")
    parser.add_argument("--model", help="Override OpenRouter model")
    parser.add_argument("--output", choices=['json', 'text'], default='text', help="Output format")

    args = parser.parse_args()

    api_client = APIClient()
    config = load_config()
    analyzer = ProfileAnalyzer(api_client, config=config)

    if args.model:
        analyzer.default_model = args.model

    result = analyzer.analyze_profile(args.profile)

    if args.output == 'json':
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            if "suggestion" in result:
                print(f"Suggestion: {result['suggestion']}", file=sys.stderr)
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"TWITTER PROFILE ANALYSIS: @{result['username']}")
        print(f"{'='*60}")

        if result.get("bio"):
            print(f"\nBio: {result['bio']}")

        # Niche
        niche = result["niche"]
        print(f"\n--- NICHE ---")
        print(f"Primary: {niche.get('primary_niche', 'unknown')}")
        if niche.get("sub_topics"):
            print(f"Sub-topics: {', '.join(niche['sub_topics'])}")
        if niche.get("positioning"):
            print(f"Positioning: {niche['positioning']}")
        if niche.get("audience"):
            print(f"Audience: {niche['audience']}")
        if niche.get("content_pillars"):
            print(f"Content pillars: {', '.join(niche['content_pillars'])}")
        if niche.get("differentiator"):
            print(f"Differentiator: {niche['differentiator']}")
        method = niche.get("method", "unknown")
        print(f"(detected via {method})")

        # Style
        style = result["style"]
        print(f"\n--- STYLE ---")
        print(f"Length: {style['length']} ({style['avg_chars']} chars avg)")
        print(f"Emojis: {style['emoji_usage']}")
        print(f"Hashtags: {style['hashtag_usage']}")
        print(f"Tone: {style['tone']}")

        # Content mix
        mix = result["content_mix"]
        print(f"\n--- CONTENT MIX ---")
        print(f"Original: {mix['original']} ({mix['original_pct']}%)")
        print(f"Retweets: {mix['retweets']} ({mix['retweet_pct']}%)")
        print(f"Replies: {mix['replies']}  |  Quotes: {mix['quotes']}")

        # Hashtags
        if result["hashtags"]:
            print(f"\n--- COMMON HASHTAGS ---")
            for tag in result["hashtags"][:5]:
                print(f"  {tag}")
        else:
            print(f"\n--- HASHTAGS: None used ---")

        # Posting
        pattern = result["posting_pattern"]
        print(f"\n--- POSTING ---")
        print(f"Frequency: {pattern['frequency']}")

        # Tweets analyzed
        ta = result["tweets_analyzed"]
        print(f"\nAnalyzed: {ta['original']} original / {ta['total']} total tweets")
        print()


if __name__ == "__main__":
    main()
