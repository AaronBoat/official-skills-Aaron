#!/usr/bin/env python3
"""
Twitter Analyzer for Creator Insights
Comprehensive Twitter/X analysis including threads, viral patterns, and engagement.
"""

import argparse
import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from api_client import APIClient
from content_generator import _is_original_tweet, _extract_style_profile, load_config
from ascii_formatter import (
    create_header, create_section_header, create_progress_bar,
    create_metric_bar, create_ranking_list, create_info_panel,
    wrap_in_box, format_number, colorize, Colors
)


class TwitterAnalyzer:
    """Analyzes Twitter accounts, tweets, and trends"""

    def __init__(self, api_client: APIClient, config: Optional[Dict] = None):
        self.api_client = api_client
        self.config = config or load_config()
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

        or_config = self.config.get("openrouter", {})
        self.default_model = or_config.get("default_model", "openai/gpt-4o-mini")
        self.default_temperature = or_config.get("temperature", 0.7)

    def _call_openrouter(self, messages: List[Dict], max_tokens: int = 800) -> Optional[str]:
        """Call OpenRouter for AI-powered analysis. Returns None if unavailable."""
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

    def analyze_account(self, username: str, num_tweets: int = 100, tz_offset: int = 0) -> Dict:
        """
        Comprehensive analysis of a Twitter account.

        Args:
            username: Twitter username (without @)
            num_tweets: Number of recent tweets to analyze
            tz_offset: Hours offset from UTC (e.g. 8 for SGT, -5 for EST)

        Returns:
            Dict with complete account analysis
        """
        print(f"Analyzing Twitter account @{username}...", file=sys.stderr)

        # Get user profile
        user_info = self.api_client.get_twitter_user_info(username)
        if not user_info:
            return {"error": f"Could not fetch info for @{username}"}

        # Get recent tweets
        tweets = self.api_client.get_twitter_user_timeline(username, num_tweets)
        if not tweets:
            return {"error": f"Could not fetch tweets for @{username}"}

        # Perform various analyses
        analysis = {
            "profile": user_info,
            "content_analysis": self._analyze_content_patterns(tweets),
            "engagement_metrics": self._calculate_twitter_engagement(tweets, user_info),
            "thread_analysis": self._analyze_threads(tweets),
            "hashtag_performance": self._analyze_hashtag_performance(tweets),
            "viral_content": self._identify_viral_tweets(tweets),
            "posting_schedule": self._analyze_posting_schedule(tweets, tz_offset),
            "content_types": self._categorize_tweet_types(tweets),
            "recommendations": self._generate_twitter_recommendations(tweets, user_info, tz_offset)
        }

        return analysis

    def _analyze_content_patterns(self, tweets: List[Dict]) -> Dict:
        """Analyze content patterns and themes using AI."""
        # Filter to originals for theme analysis
        originals = [t for t in tweets if _is_original_tweet(t)]
        if not originals:
            originals = tweets

        # Basic metrics
        question_count = sum(1 for t in originals if '?' in t["text"])
        exclamation_count = sum(1 for t in originals if '!' in t["text"])
        emoji_count = sum(len([c for c in t["text"] if ord(c) > 0x1F300]) for t in originals)
        avg_length = sum(len(t["text"]) for t in originals) / len(originals) if originals else 0

        # AI-powered theme extraction
        themes = self._extract_themes_ai(originals)

        return {
            "themes": themes or [],
            "avg_tweet_length": avg_length,
            "questions_percentage": (question_count / len(originals) * 100) if originals else 0,
            "exclamations_percentage": (exclamation_count / len(originals) * 100) if originals else 0,
            "emoji_usage": emoji_count / len(originals) if originals else 0
        }

    def _extract_themes_ai(self, originals: List[Dict]) -> Optional[List[str]]:
        """Use AI to extract meaningful content themes from tweets."""
        scored = []
        for t in originals:
            eng = t["likes"] + t["retweets"] + t["replies"]
            scored.append((eng, t["text"]))
        scored.sort(reverse=True)
        sample_texts = "\n".join(f"- {text}" for _, text in scored[:15])

        prompt = f"""Look at these tweets and identify the 5-8 specific content themes this person posts about.

Be specific and granular — not "crypto" but "Solana token launches." Not "tech" but "AI coding tools." Use the actual topics, projects, and subjects you see.

Tweets:
{sample_texts}

Return a JSON array of theme strings, nothing else. Example: ["Solana ecosystem updates", "crypto market timing calls", "DeFi infrastructure commentary"]"""

        messages = [{"role": "user", "content": prompt}]
        ai_response = self._call_openrouter(messages, max_tokens=300)

        if not ai_response:
            return None

        try:
            json_start = ai_response.find('[')
            json_end = ai_response.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                themes = json.loads(ai_response[json_start:json_end])
                if isinstance(themes, list) and themes:
                    return themes[:8]
        except json.JSONDecodeError:
            pass

        return None

    def _calculate_twitter_engagement(self, tweets: List[Dict], user_info: Dict) -> Dict:
        """Calculate Twitter-specific engagement metrics"""
        if not tweets:
            return {}

        total_likes = sum(t["likes"] for t in tweets)
        total_retweets = sum(t["retweets"] for t in tweets)
        total_replies = sum(t["replies"] for t in tweets)
        total_quotes = sum(t["quotes"] for t in tweets)

        # Calculate engagement rate based on followers
        followers = user_info.get("followers_count", 1)
        avg_engagement = (total_likes + total_retweets + total_replies) / len(tweets)
        engagement_rate = (avg_engagement / followers * 100) if followers > 0 else 0

        # Like to RT ratio (higher = more passive engagement)
        like_to_rt_ratio = total_likes / total_retweets if total_retweets > 0 else 0

        # Reply rate (indicator of conversation quality)
        reply_rate = (total_replies / len(tweets)) if tweets else 0

        return {
            "total_likes": total_likes,
            "total_retweets": total_retweets,
            "total_replies": total_replies,
            "total_quotes": total_quotes,
            "avg_likes_per_tweet": total_likes / len(tweets),
            "avg_retweets_per_tweet": total_retweets / len(tweets),
            "avg_replies_per_tweet": reply_rate,
            "engagement_rate": round(engagement_rate, 3),
            "like_to_rt_ratio": round(like_to_rt_ratio, 2),
            "total_engagement": total_likes + total_retweets + total_replies + total_quotes
        }

    def _analyze_threads(self, tweets: List[Dict]) -> Dict:
        """Analyze thread usage and performance"""
        # Count replies (threads are usually replies to own tweets)
        reply_tweets = [t for t in tweets if t["is_reply"]]
        thread_count = len(reply_tweets)

        # Get average engagement on threads vs standalone
        if reply_tweets:
            thread_engagement = sum(t["likes"] + t["retweets"] + t["replies"] for t in reply_tweets) / len(reply_tweets)
        else:
            thread_engagement = 0

        standalone_tweets = [t for t in tweets if not t["is_reply"]]
        if standalone_tweets:
            standalone_engagement = sum(t["likes"] + t["retweets"] + t["replies"] for t in standalone_tweets) / len(standalone_tweets)
        else:
            standalone_engagement = 0

        return {
            "thread_count": thread_count,
            "thread_percentage": (thread_count / len(tweets) * 100) if tweets else 0,
            "avg_thread_engagement": round(thread_engagement, 1),
            "avg_standalone_engagement": round(standalone_engagement, 1),
            "threads_perform_better": thread_engagement > standalone_engagement
        }

    def _analyze_hashtag_performance(self, tweets: List[Dict]) -> Dict:
        """Analyze hashtag usage and performance"""
        # Collect all hashtags with their tweet's engagement
        hashtag_performance = defaultdict(lambda: {"count": 0, "total_engagement": 0, "tweets": []})

        for tweet in tweets:
            engagement = tweet["likes"] + tweet["retweets"] + tweet["replies"]
            for hashtag in tweet["hashtags"]:
                hashtag_performance[hashtag]["count"] += 1
                hashtag_performance[hashtag]["total_engagement"] += engagement
                hashtag_performance[hashtag]["tweets"].append(tweet["id"])

        # Calculate average engagement per hashtag
        hashtag_stats = []
        for hashtag, data in hashtag_performance.items():
            avg_engagement = data["total_engagement"] / data["count"] if data["count"] > 0 else 0
            hashtag_stats.append({
                "hashtag": f"#{hashtag}",
                "times_used": data["count"],
                "avg_engagement": round(avg_engagement, 1)
            })

        # Sort by average engagement
        hashtag_stats.sort(key=lambda x: x["avg_engagement"], reverse=True)

        # Overall hashtag usage
        tweets_with_hashtags = len([t for t in tweets if t["hashtags"]])
        avg_hashtags_per_tweet = sum(len(t["hashtags"]) for t in tweets) / len(tweets) if tweets else 0

        return {
            "tweets_with_hashtags": tweets_with_hashtags,
            "hashtag_usage_percentage": (tweets_with_hashtags / len(tweets) * 100) if tweets else 0,
            "avg_hashtags_per_tweet": round(avg_hashtags_per_tweet, 2),
            "top_hashtags": hashtag_stats[:10],
            "best_performing_hashtag": hashtag_stats[0] if hashtag_stats else None
        }

    def _identify_viral_tweets(self, tweets: List[Dict], threshold_multiplier: float = 2.0) -> List[Dict]:
        """Identify viral tweets (those with significantly above-average engagement)"""
        if not tweets:
            return []

        # Calculate average engagement
        avg_engagement = sum(t["likes"] + t["retweets"] + t["replies"] for t in tweets) / len(tweets)

        # Find tweets exceeding threshold
        viral_threshold = avg_engagement * threshold_multiplier

        viral_tweets = []
        for tweet in tweets:
            engagement = tweet["likes"] + tweet["retweets"] + tweet["replies"]
            if engagement >= viral_threshold:
                viral_tweets.append({
                    "text": tweet["text"][:100] + "..." if len(tweet["text"]) > 100 else tweet["text"],
                    "likes": tweet["likes"],
                    "retweets": tweet["retweets"],
                    "replies": tweet["replies"],
                    "total_engagement": engagement,
                    "engagement_multiplier": round(engagement / avg_engagement, 1),
                    "url": tweet["url"],
                    "created_at": tweet["created_at"],
                    "has_media": len(tweet.get("urls", [])) > 0,
                    "hashtags": tweet["hashtags"]
                })

        # Sort by engagement
        viral_tweets.sort(key=lambda x: x["total_engagement"], reverse=True)

        return viral_tweets[:5]  # Top 5 viral tweets

    def _analyze_posting_schedule(self, tweets: List[Dict], tz_offset: int = 0) -> Dict:
        """Analyze when the account posts, adjusted to the creator's timezone."""
        # Require at least 5 tweets for meaningful posting schedule analysis
        if len(tweets) < 5:
            tz_label = f"UTC{tz_offset:+d}" if tz_offset != 0 else "UTC"
            return {
                "most_active_hours": [],
                "most_active_days": [],
                "best_performing_hours": [],
                "posts_per_day": len(tweets) / 30,
                "timezone": tz_label,
                "warning": f"Insufficient data: only {len(tweets)} tweets found. Use longer timeframe (--timeframe '30d' or '7d') for posting schedule analysis."
            }

        # Group tweets by hour and day
        hour_distribution = defaultdict(int)
        day_distribution = defaultdict(int)
        engagement_by_hour = defaultdict(lambda: {"count": 0, "total_engagement": 0})

        tz_delta = timedelta(hours=tz_offset)

        for tweet in tweets:
            if not tweet["created_at"]:
                continue

            try:
                # Twitter uses format: "Mon Mar 30 07:55:14 +0000 2026"
                # Try ISO format first, then Twitter format
                created_at_str = tweet["created_at"]
                try:
                    dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                except:
                    # Parse Twitter's date format
                    dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")

                # Convert from UTC to creator's local timezone
                local_dt = dt + tz_delta
                hour = local_dt.hour
                day = local_dt.strftime("%A")

                hour_distribution[hour] += 1
                day_distribution[day] += 1

                engagement = tweet["likes"] + tweet["retweets"] + tweet["replies"]
                engagement_by_hour[hour]["count"] += 1
                engagement_by_hour[hour]["total_engagement"] += engagement
            except Exception as e:
                # Silently skip tweets with unparseable dates
                pass

        # Find best posting times
        best_hours = []
        for hour, data in engagement_by_hour.items():
            if data["count"] > 0:
                avg_engagement = data["total_engagement"] / data["count"]
                best_hours.append({
                    "hour": hour,
                    "posts": data["count"],
                    "avg_engagement": round(avg_engagement, 1)
                })

        best_hours.sort(key=lambda x: x["avg_engagement"], reverse=True)

        tz_label = f"UTC{tz_offset:+d}" if tz_offset != 0 else "UTC"
        return {
            "most_active_hours": sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
            "most_active_days": sorted(day_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
            "best_performing_hours": best_hours[:5],
            "posts_per_day": len(tweets) / 30,  # Assuming ~30 days of data
            "timezone": tz_label
        }

    def _categorize_tweet_types(self, tweets: List[Dict]) -> Dict:
        """Categorize tweets by type and analyze performance"""
        categories = {
            "original": [],
            "replies": [],
            "quotes": [],
            "with_media": [],
            "with_hashtags": [],
            "questions": [],
            "threads": []
        }

        for tweet in tweets:
            engagement = tweet["likes"] + tweet["retweets"] + tweet["replies"]

            if not tweet["is_reply"] and not tweet["is_quote"]:
                categories["original"].append(engagement)
            if tweet["is_reply"]:
                categories["replies"].append(engagement)
                categories["threads"].append(engagement)
            if tweet["is_quote"]:
                categories["quotes"].append(engagement)
            if tweet.get("urls"):
                categories["with_media"].append(engagement)
            if tweet["hashtags"]:
                categories["with_hashtags"].append(engagement)
            if '?' in tweet["text"]:
                categories["questions"].append(engagement)

        # Calculate averages
        results = {}
        for category, engagements in categories.items():
            if engagements:
                results[category] = {
                    "count": len(engagements),
                    "avg_engagement": round(sum(engagements) / len(engagements), 1),
                    "percentage": round(len(engagements) / len(tweets) * 100, 1)
                }
            else:
                results[category] = {"count": 0, "avg_engagement": 0, "percentage": 0}

        return results

    def _generate_twitter_recommendations(self, tweets: List[Dict], user_info: Dict, tz_offset: int = 0) -> List[str]:
        """Generate recommendations using AI, aware of the creator's actual style."""
        originals = [t for t in tweets if _is_original_tweet(t)]
        if not originals:
            originals = tweets

        # Build context for AI
        style_profile = _extract_style_profile(tweets, user_info.get("username", "unknown"))
        engagement = self._calculate_twitter_engagement(tweets, user_info)
        schedule = self._analyze_posting_schedule(tweets, tz_offset)
        hashtag_perf = self._analyze_hashtag_performance(tweets)
        thread_analysis = self._analyze_threads(tweets)

        # Try AI recommendations
        ai_recs = self._generate_recommendations_ai(
            originals, user_info, style_profile, engagement, schedule, hashtag_perf, thread_analysis
        )
        if ai_recs:
            return ai_recs

        # Fallback: basic posting time recommendation
        recs = []
        if schedule["best_performing_hours"]:
            best_hour = schedule["best_performing_hours"][0]["hour"]
            tz_label = schedule["timezone"]
            recs.append(f"Your tweets at {best_hour:02d}:00 ({tz_label}) perform best - post more at this time")
        return recs

    def _generate_recommendations_ai(self, originals: List[Dict], user_info: Dict,
                                     style_profile: Dict, engagement: Dict,
                                     schedule: Dict, hashtag_perf: Dict,
                                     thread_analysis: Dict) -> Optional[List[str]]:
        """Use AI to generate style-aware recommendations."""
        # Build top tweets sample
        scored = []
        for t in originals:
            eng = t["likes"] + t["retweets"] + t["replies"]
            scored.append((eng, t["text"]))
        scored.sort(reverse=True)
        top_tweets = "\n".join(f"- ({eng:,} eng) {text[:100]}" for eng, text in scored[:8])

        tz_label = schedule.get("timezone", "UTC")
        best_hours = ", ".join(f"{h['hour']:02d}:00" for h in schedule.get("best_performing_hours", [])[:3])

        prompt = f"""Analyze this Twitter account and give 5-7 specific, actionable growth recommendations.

IMPORTANT: Respect the creator's established style. Do NOT recommend things that contradict how they already operate. If they don't use hashtags, don't tell them to start. If they don't thread, don't push threads. Instead, find ways to amplify what already works.

Account: @{user_info.get('username', 'unknown')}
Followers: {user_info.get('followers_count', 0):,}
Engagement rate: {engagement.get('engagement_rate', 0):.1f}%
Avg likes/tweet: {engagement.get('avg_likes_per_tweet', 0):.0f}
Posts/day: {schedule.get('posts_per_day', 0):.1f}
Best posting hours ({tz_label}): {best_hours}

Style profile:
- {style_profile.get('length_style', 'unknown')} tweets (avg {style_profile.get('avg_length', 0):.0f} chars)
- {style_profile.get('emoji_style', 'unknown')}
- {style_profile.get('hashtag_style', 'unknown')}
- {style_profile.get('tone', 'unknown')} tone
- Thread usage: {thread_analysis.get('thread_percentage', 0):.0f}% of tweets

Top performing tweets:
{top_tweets}

Return a JSON array of 5-7 recommendation strings. Each should be 1-2 sentences, specific to THIS account. No generic advice.

Example format: ["Your one-liner format drives strong engagement — try more of the short observation style that got 5K+ likes", "Post more during 18:00-19:00 UTC when your audience is most active"]

Return ONLY the JSON array."""

        messages = [{"role": "user", "content": prompt}]
        ai_response = self._call_openrouter(messages, max_tokens=600)

        if not ai_response:
            return None

        try:
            json_start = ai_response.find('[')
            json_end = ai_response.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                recs = json.loads(ai_response[json_start:json_end])
                if isinstance(recs, list) and recs:
                    return recs[:7]
        except json.JSONDecodeError:
            pass

        return None

    def find_trending_in_niche(self, niche: str, max_tweets: int = 50) -> Dict:
        """
        Find trending content in a specific niche.

        Args:
            niche: Niche or topic to search
            max_tweets: Number of tweets to analyze

        Returns:
            Dict with trending analysis
        """
        print(f"Searching for trending {niche} content on Twitter...", file=sys.stderr)

        # Search for recent popular tweets
        query = f"{niche} min_faves:100 -is:retweet"  # Tweets with at least 100 likes
        tweets = self.api_client.search_twitter_tweets(query, max_tweets)

        if not tweets:
            return {"error": f"No tweets found for {niche}"}

        # Analyze trending patterns
        hashtags_counter = Counter()
        mentions_counter = Counter()
        top_tweets = []

        for tweet in tweets:
            hashtags_counter.update(tweet["hashtags"])
            mentions_counter.update(tweet["mentions"])

            engagement = tweet["likes"] + tweet["retweets"] + tweet["replies"]
            top_tweets.append({
                "text": tweet["text"][:100] + "..." if len(tweet["text"]) > 100 else tweet["text"],
                "author": tweet.get("author", {}).get("username", "Unknown"),
                "engagement": engagement,
                "likes": tweet["likes"],
                "retweets": tweet["retweets"],
                "url": tweet["url"]
            })

        # Sort by engagement
        top_tweets.sort(key=lambda x: x["engagement"], reverse=True)

        return {
            "niche": niche,
            "tweets_analyzed": len(tweets),
            "trending_hashtags": [{"tag": f"#{tag}", "count": count} for tag, count in hashtags_counter.most_common(10)],
            "popular_accounts": [{"username": f"@{user}", "mentions": count} for user, count in mentions_counter.most_common(10)],
            "top_performing_tweets": top_tweets[:10]
        }


def main():
    """CLI interface for Twitter analyzer"""
    parser = argparse.ArgumentParser(description="Analyze Twitter accounts and trends")
    parser.add_argument("--username", help="Twitter username to analyze (without @)")
    parser.add_argument("--niche", help="Find trending content in a niche")
    parser.add_argument("--tweets", type=int, default=100, help="Number of tweets to analyze")
    parser.add_argument("--timezone", type=int, default=0, help="UTC offset in hours (e.g. 8 for SGT, -5 for EST)")
    parser.add_argument("--output", choices=['json', 'text'], default='text', help="Output format")

    args = parser.parse_args()

    if not args.username and not args.niche:
        print("Error: Provide either --username or --niche", file=sys.stderr)
        sys.exit(1)

    # Initialize
    api_client = APIClient()
    analyzer = TwitterAnalyzer(api_client)

    # Execute analysis
    if args.username:
        result = analyzer.analyze_account(args.username, args.tweets, args.timezone)
    else:
        result = analyzer.find_trending_in_niche(args.niche, args.tweets)

    # Output
    if args.output == 'json':
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        # Format text output with ASCII art
        if args.username:
            profile = result["profile"]
            eng = result["engagement_metrics"]

            # Header
            print(create_header(f"  TWITTER ANALYSIS: @{args.username}  ", 70))

            # Profile Card
            followers_formatted = f"{profile['followers_count']:,}"
            profile_info = [
                f"Name: {colorize(profile['name'], Colors.BRIGHT_CYAN)}",
                f"Followers: {colorize(followers_formatted, Colors.BRIGHT_GREEN)}",
                f"Following: {profile['following_count']:,}",
                f"Total Tweets: {profile['tweet_count']:,}",
                f"Verified: {colorize('✓ Yes', Colors.BRIGHT_GREEN) if profile['verified'] else 'No'}"
            ]
            print(create_info_panel("👤", "Profile Information", profile_info, 70))

            # Engagement Metrics with Progress Bars
            print(create_section_header("📊 ENGAGEMENT METRICS", 70))

            # Find max values for progress bars
            max_likes = max(eng['avg_likes_per_tweet'], 100)
            max_retweets = max(eng['avg_retweets_per_tweet'], 20)
            max_replies = max(eng['avg_replies_per_tweet'], 10)

            print(create_metric_bar("Engagement Rate", eng['engagement_rate'], 5.0, width=70))
            print(create_metric_bar("Avg Likes", eng['avg_likes_per_tweet'], max_likes, width=70))
            print(create_metric_bar("Avg Retweets", eng['avg_retweets_per_tweet'], max_retweets, width=70))
            print(create_metric_bar("Avg Replies", eng['avg_replies_per_tweet'], max_replies, width=70))
            print(f"\n  {'Like/RT Ratio':<20} {eng['like_to_rt_ratio']:.2f} {'(Higher = more passive engagement)':>28}")
            print(f"  {'Total Engagement':<20} {colorize(format_number(eng['total_engagement']), Colors.BRIGHT_YELLOW):>10}")

            # Viral Content Ranking
            if result["viral_content"]:
                viral_items = []
                for i, tweet in enumerate(result["viral_content"][:5], 1):
                    label = f"{tweet['text'][:40]}..."
                    value = tweet['total_engagement']
                    viral_items.append((i, label, value))

                print("\n" + create_ranking_list(viral_items, "VIRAL TWEETS", 70, show_bars=True))

                # Show details of top viral tweet
                if result["viral_content"]:
                    top_viral = result["viral_content"][0]
                    multiplier_text = f"{top_viral['engagement_multiplier']}x above average"
                    print(f"\n  {'Top Viral Tweet Details:':^70}")
                    print(f"  {'-' * 68}")
                    print(f"  💬 {top_viral['text'][:60]}")
                    print(f"  ❤️  {top_viral['likes']:,} likes  |  🔄 {top_viral['retweets']:,} RTs  |  💭 {top_viral['replies']:,} replies")
                    print(f"  🔥 {colorize(multiplier_text, Colors.BRIGHT_RED)}")

            # Recommendations Panel
            print(create_info_panel("💡", "RECOMMENDATIONS", result["recommendations"][:7], 70))

            # Thread Analysis
            thread_analysis = result["thread_analysis"]
            if thread_analysis["thread_count"] > 0:
                print(create_section_header("🧵 THREAD ANALYSIS", 70))
                print(f"  Thread Usage: {thread_analysis['thread_percentage']:.1f}% of tweets")
                print(f"  Avg Thread Engagement: {format_number(thread_analysis['avg_thread_engagement'])}")
                print(f"  Avg Standalone Engagement: {format_number(thread_analysis['avg_standalone_engagement'])}")
                if thread_analysis["threads_perform_better"]:
                    print(f"  {colorize('✓ Threads perform better!', Colors.BRIGHT_GREEN)}")
                else:
                    print(f"  Standalone tweets perform better")

            # Best Posting Times
            schedule = result["posting_schedule"]
            if schedule["best_performing_hours"]:
                tz_label = schedule.get("timezone", "UTC")
                print(create_section_header(f"⏰ BEST POSTING TIMES ({tz_label})", 70))
                for hour_data in schedule["best_performing_hours"][:3]:
                    hour = hour_data["hour"]
                    avg_eng = hour_data["avg_engagement"]
                    print(f"  {hour:02d}:00 - Avg engagement: {colorize(format_number(avg_eng), Colors.BRIGHT_YELLOW)}")
                if tz_label == "UTC":
                    top_hour = schedule["best_performing_hours"][0]["hour"]
                    print(f"\n  Note: Times are UTC. Use --timezone to convert to local time.")
                    print(f"  Examples: {top_hour:02d}:00 UTC = {(top_hour+8)%24:02d}:00 SGT/AEST-2 = {(top_hour-5)%24:02d}:00 EST = {(top_hour-8)%24:02d}:00 PST")

            print()

        else:  # Niche search with ASCII art
            print(create_header(f"  TRENDING: {result['niche'].upper()}  ", 70))

            print(f"\n  📊 Tweets Analyzed: {colorize(str(result['tweets_analyzed']), Colors.BRIGHT_CYAN)}\n")

            # Trending Hashtags
            if result["trending_hashtags"]:
                print(create_section_header("🔥 TRENDING HASHTAGS", 70))
                hashtag_items = []
                for i, tag in enumerate(result["trending_hashtags"][:8], 1):
                    hashtag_items.append((i, tag['tag'], tag['count']))
                print(create_ranking_list(hashtag_items, "", 70, show_bars=True))

            # Top Performing Tweets
            if result["top_performing_tweets"]:
                tweet_items = []
                for i, tweet in enumerate(result["top_performing_tweets"][:10], 1):
                    label = f"@{tweet['author']}: {tweet['text'][:35]}"
                    value = tweet['engagement']
                    tweet_items.append((i, label, value))

                print("\n" + create_ranking_list(tweet_items, "TOP PERFORMING TWEETS", 70, show_bars=True))

                # Show details of top tweet
                top_tweet = result["top_performing_tweets"][0]
                print(f"\n  {'Top Tweet Details:':^70}")
                print(f"  {'-' * 68}")
                print(f"  👤 @{colorize(top_tweet['author'], Colors.BRIGHT_CYAN)}")
                print(f"  💬 {top_tweet['text'][:60]}")
                print(f"  ❤️  {top_tweet['likes']:,} likes  |  🔄 {top_tweet['retweets']:,} RTs")
                print(f"  📈 Total: {colorize(format_number(top_tweet['engagement']), Colors.BRIGHT_YELLOW)} engagement")

            print()


if __name__ == "__main__":
    main()
