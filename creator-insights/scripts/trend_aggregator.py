#!/usr/bin/env python3
"""
Twitter Trend Aggregator for Creator Insights
Discovers trending content and accounts on Twitter/X.
"""

import argparse
import sys
import json
from typing import Dict, List, Optional
from api_client import APIClient
from content_generator import _is_branded_account
from ascii_formatter import (
    create_header, create_section_header, create_ranking_list,
    create_info_panel, format_number, colorize, Colors
)


class TrendAggregator:
    """Aggregates trending content from Twitter/X"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def get_twitter_trends(self, niche: Optional[str] = None) -> List[Dict]:
        """
        Fetch trending content from Twitter/X.

        Args:
            niche: Content niche to search for trending tweets

        Returns:
            List of trending topics/tweets
        """
        print(f"Fetching Twitter trends...", file=sys.stderr)

        if niche:
            # Search for trending tweets in the niche
            query = f"{niche} min_faves:100 -is:retweet"
            tweets = self.api_client.search_twitter_tweets(query, "Top", max_results=20)

            trends = []
            for tweet in tweets[:10]:
                trends.append({
                    "type": "tweet",
                    "content": tweet['text'][:100] + "..." if len(tweet['text']) > 100 else tweet['text'],
                    "author": tweet.get('author', {}).get('username', 'Unknown'),
                    "metric": f"{tweet['likes']:,} likes, {tweet['retweets']:,} RTs",
                    "url": tweet.get('url', '')
                })
            return trends
        else:
            # Return general trending pattern
            return [{
                "type": "info",
                "content": "Specify a niche to search for trending tweets",
                "metric": "Use --niche parameter"
            }]

    def find_trending_accounts(self, niche: str, limit: int = 5,
                              filter_branded: bool = False) -> List[Dict]:
        """
        Find trending Twitter accounts in a specific niche.

        Args:
            niche: Content niche to search
            limit: Number of accounts to return
            filter_branded: If True, exclude branded/corporate accounts

        Returns:
            List of account information
        """
        print(f"Finding trending Twitter accounts in {niche}...", file=sys.stderr)

        # Search for popular tweets in niche and extract top authors
        query = f"{niche} min_faves:500 -is:retweet"
        tweets = self.api_client.search_twitter_tweets(query, "Top", max_results=50)

        # Count authors and their engagement
        from collections import defaultdict
        author_stats = defaultdict(lambda: {"tweets": 0, "total_engagement": 0, "sample_tweets": []})

        for tweet in tweets:
            author = tweet.get('author', {})
            username = author.get('username')
            if username:
                engagement = tweet['likes'] + tweet['retweets'] + tweet['replies']
                author_stats[username]["tweets"] += 1
                author_stats[username]["total_engagement"] += engagement
                author_stats[username]["author_info"] = author
                if len(author_stats[username]["sample_tweets"]) < 1:
                    author_stats[username]["sample_tweets"].append(tweet['text'][:80])

        # Sort by total engagement
        sorted_authors = sorted(author_stats.items(), key=lambda x: x[1]["total_engagement"], reverse=True)

        accounts = []
        branded_filtered = 0
        for username, stats in sorted_authors:
            if len(accounts) >= limit:
                break

            author_info = stats["author_info"]
            is_branded = _is_branded_account(author_info)

            if filter_branded and is_branded:
                branded_filtered += 1
                continue

            accounts.append({
                "username": username,
                "platform": "twitter",
                "followers": author_info.get("followers", 0),
                "total_engagement": stats["total_engagement"],
                "tweets_found": stats["tweets"],
                "sample_content": stats["sample_tweets"][0] if stats["sample_tweets"] else "",
                "is_branded": is_branded
            })

        if branded_filtered > 0:
            print(f"Filtered out {branded_filtered} branded accounts", file=sys.stderr)

        return accounts

    def get_viral_examples(self, niche: str, limit: int = 5,
                          filter_branded: bool = False) -> List[Dict]:
        """
        Get examples of recent viral tweets in a niche.

        Args:
            niche: Content niche
            limit: Number of examples to return
            filter_branded: If True, exclude tweets from branded/corporate accounts

        Returns:
            List of viral tweet examples with analysis
        """
        print(f"Finding viral tweets in {niche}...", file=sys.stderr)

        # Fetch extra results to account for filtering
        fetch_limit = limit * 4 if filter_branded else limit * 2
        query = f"{niche} min_faves:1000 -is:retweet"
        tweets = self.api_client.search_twitter_tweets(query, "Top", max_results=fetch_limit)

        viral_content = []
        branded_filtered = 0
        for tweet in tweets:
            if len(viral_content) >= limit:
                break

            author = tweet.get('author', {})
            is_branded = _is_branded_account(author)

            if filter_branded and is_branded:
                branded_filtered += 1
                continue

            engagement = tweet['likes'] + tweet['retweets'] + tweet['replies']
            viral_content.append({
                "platform": "twitter",
                "type": "tweet",
                "content": tweet['text'],
                "creator": f"@{author.get('username', 'Unknown')}",
                "is_branded": is_branded,
                "engagement": f"{tweet['likes']:,} likes, {tweet['retweets']:,} RTs, {tweet['replies']:,} replies",
                "total_engagement": engagement,
                "url": tweet.get('url', ''),
                "hashtags": tweet.get('hashtags', []),
                "why_viral": self._analyze_viral_factors(tweet)
            })

        return viral_content

    def _analyze_viral_factors(self, tweet: Dict) -> str:
        """
        Analyze why a tweet went viral with enhanced pattern detection.

        Detects:
        - Content format (questions, threads, lists, emotional hooks)
        - Media usage (images, videos, GIFs)
        - Engagement patterns (likes vs retweets vs replies ratio)
        - Temporal patterns (posting time optimization)
        - Hashtag strategy
        - Call-to-action presence
        """
        text = tweet.get('text', '') if 'text' in tweet else tweet.get('content', '')
        text_lower = text.lower()
        hashtags = tweet.get('hashtags', [])
        urls = tweet.get('urls', [])

        # Engagement metrics
        likes = tweet.get('likes', 0)
        retweets = tweet.get('retweets', 0)
        replies = tweet.get('replies', 0)
        quotes = tweet.get('quotes', 0)
        total_engagement = likes + retweets + replies + quotes

        factors = []

        # === 1. FORMAT DETECTION ===

        # Thread detection
        if 'thread' in text_lower or '🧵' in text or '1/' in text or '(thread)' in text_lower:
            factors.append("multi-tweet thread format")

        # Question format (highly engaging)
        question_count = text.count('?')
        if question_count >= 2:
            factors.append("multiple questions driving discussion")
        elif question_count == 1:
            factors.append("question encouraging replies")

        # List/numbered format
        if any(f"{i}." in text or f"{i})" in text for i in range(1, 6)):
            factors.append("structured list format")

        # Emotional hooks
        emotional_words = ['amazing', 'incredible', 'shocking', 'important', 'urgent',
                          'breaking', 'huge', 'just', 'wow', 'omg', 'insane', 'wild']
        if any(word in text_lower for word in emotional_words):
            factors.append("emotional hook driving curiosity")

        # Call-to-action
        cta_phrases = ['check out', 'let me know', 'drop a', 'reply with', 'share if',
                       'rt if', 'comment', 'tell me', 'what do you think']
        if any(phrase in text_lower for phrase in cta_phrases):
            factors.append("clear call-to-action")

        # === 2. MEDIA DETECTION ===

        # Check for media presence (photos, videos, GIFs)
        has_media = len(urls) > 0 or 'photo' in text_lower or 'video' in text_lower
        if has_media:
            factors.append("visual content (image/video)")

        # === 3. LENGTH OPTIMIZATION ===

        text_length = len(text)
        if text_length > 240:
            factors.append("comprehensive detail (long-form)")
        elif text_length < 80:
            factors.append("highly concise and punchy")
        elif 120 <= text_length <= 180:
            factors.append("optimal length for readability")

        # === 4. HASHTAG STRATEGY ===

        hashtag_count = len(hashtags)
        if hashtag_count >= 3:
            factors.append(f"strategic use of {hashtag_count} hashtags")
        elif hashtag_count == 1:
            factors.append("focused single hashtag")

        # === 5. ENGAGEMENT PATTERN ANALYSIS ===

        if total_engagement > 0:
            # Calculate engagement ratios
            like_ratio = likes / total_engagement
            retweet_ratio = retweets / total_engagement
            reply_ratio = replies / total_engagement

            # High reply ratio = conversation starter
            if reply_ratio > 0.25:
                factors.append("sparked active discussion (high replies)")

            # High retweet ratio = shareworthy
            if retweet_ratio > 0.20:
                factors.append("highly shareable content")

            # Viral coefficient (quotes + retweets)
            if quotes > 0 and (quotes + retweets) / total_engagement > 0.30:
                factors.append("viral amplification pattern")

        # === 6. TEMPORAL ANALYSIS (if created_at available) ===

        created_at = tweet.get('created_at')
        if created_at:
            try:
                from datetime import datetime
                # Parse timestamp
                if isinstance(created_at, str):
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    hour = dt.hour
                    day_of_week = dt.strftime('%A')

                    # Optimal posting times
                    if 9 <= hour <= 11 or 13 <= hour <= 15:
                        factors.append(f"posted during peak engagement window")
                    elif hour >= 21 or hour <= 6:
                        factors.append("posted during low-competition hours")

                    # Weekend posting
                    if day_of_week in ['Saturday', 'Sunday']:
                        factors.append("weekend timing advantage")
            except:
                pass

        # === 7. ADVANCED PATTERNS ===

        # Authority signaling
        if any(word in text_lower for word in ['study', 'research', 'data', 'analysis', 'found']):
            factors.append("data-driven credibility")

        # Storytelling
        if any(word in text_lower for word in ['story', 'remember when', 'last week', 'yesterday']):
            factors.append("narrative storytelling hook")

        # Controversy/debate
        if any(word in text_lower for word in ['unpopular opinion', 'hot take', 'controversial', 'debate']):
            factors.append("controversial take driving debate")

        # If no specific factors identified
        if not factors:
            # Fallback analysis based on engagement type
            if replies > likes:
                factors.append("discussion-focused content")
            elif retweets > likes:
                factors.append("highly newsworthy/shareable")
            else:
                factors.append("strong content and timing")

        # Return top 4 factors for conciseness
        return "; ".join(factors[:4]).capitalize()


def main():
    """CLI interface for Twitter trend aggregator"""
    parser = argparse.ArgumentParser(description="Find trending content on Twitter")
    parser.add_argument("--niche", help="Content niche to search for trends")
    parser.add_argument("--find-accounts", action="store_true",
                       help="Find trending accounts in the niche")
    parser.add_argument("--viral-examples", action="store_true",
                       help="Get viral tweet examples")
    parser.add_argument("--limit", type=int, default=5,
                       help="Number of results to return")
    parser.add_argument("--filter-branded", action="store_true",
                       help="Filter out branded/corporate accounts (show only organic creators)")
    parser.add_argument("--output", choices=['json', 'text'], default='text',
                       help="Output format")

    args = parser.parse_args()

    # Initialize API client and aggregator
    api_client = APIClient()
    aggregator = TrendAggregator(api_client)

    # Execute requested action
    if args.find_accounts:
        if not args.niche:
            print("Error: --niche is required for account discovery", file=sys.stderr)
            sys.exit(1)
        result = aggregator.find_trending_accounts(args.niche, args.limit, args.filter_branded)
    elif args.viral_examples:
        if not args.niche:
            print("Error: --niche is required for viral examples", file=sys.stderr)
            sys.exit(1)
        result = aggregator.get_viral_examples(args.niche, args.limit, args.filter_branded)
    else:
        result = aggregator.get_twitter_trends(args.niche)

    # Output results with ASCII art
    if args.output == 'json':
        print(json.dumps(result, indent=2))
    else:
        # Create header
        header_text = f"  TWITTER TRENDING"
        if args.niche:
            header_text += f": {args.niche.upper()}  "
        else:
            header_text += " CONTENT  "
        print(create_header(header_text, 70))

        if args.find_accounts:
            if result:
                # Create ranking list for accounts
                account_items = []
                for i, account in enumerate(result, 1):
                    label = f"@{account['username']} ({format_number(account['followers'])} followers)"
                    value = account['total_engagement']
                    account_items.append((i, label, value))

                print("\n" + create_ranking_list(account_items, "TRENDING ACCOUNTS", 70, show_bars=True))

                # Show details of top account
                if result:
                    top_account = result[0]
                    username_text = f"@{top_account['username']}"
                    print(f"\n  {'Top Account Details:':^70}")
                    print(f"  {'-' * 68}")
                    print(f"  👤 {colorize(username_text, Colors.BRIGHT_CYAN)}")
                    print(f"  👥 Followers: {colorize(format_number(top_account['followers']), Colors.BRIGHT_GREEN)}")
                    print(f"  📈 Total Engagement: {colorize(format_number(top_account['total_engagement']), Colors.BRIGHT_YELLOW)}")
                    print(f"  🐦 Tweets Found: {top_account['tweets_found']}")
                    print(f"  💬 Sample: {top_account['sample_content'][:55]}...")
            else:
                print("\n  No accounts found.\n")

        elif args.viral_examples:
            if result:
                # Create ranking list for viral tweets
                viral_items = []
                for i, content in enumerate(result, 1):
                    label = f"{content['creator']}: {content['content'][:35]}"
                    value = content['total_engagement']
                    viral_items.append((i, label, value))

                print("\n" + create_ranking_list(viral_items, "VIRAL TWEETS", 70, show_bars=True))

                # Show detailed breakdown of top viral tweets
                print(create_section_header("📊 DETAILED VIRAL ANALYSIS", 70))
                for i, content in enumerate(result[:3], 1):
                    rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    print(f"\n  {rank_emoji} {colorize(content['creator'], Colors.BRIGHT_CYAN)}")
                    print(f"  💬 {content['content'][:60]}")
                    print(f"  📊 {content['engagement']}")
                    print(f"  🔥 Why viral: {colorize(content['why_viral'], Colors.BRIGHT_YELLOW)}")
                    if content.get('hashtags'):
                        hashtags_str = ', '.join(['#' + h for h in content['hashtags'][:3]])
                        print(f"  🏷️  {hashtags_str}")
                    if content.get('url'):
                        print(f"  🔗 {content['url']}")
            else:
                print("\n  No viral tweets found.\n")

        else:
            if isinstance(result, list) and result:
                # General trending tweets
                trend_items = []
                for i, trend in enumerate(result, 1):
                    if trend.get('type') != 'info':
                        label = f"@{trend.get('author', 'Unknown')}: {trend.get('content', '')[:35]}"
                        # Extract engagement number from metric
                        metric_text = trend.get('metric', '0')
                        try:
                            likes = int(metric_text.split('likes')[0].replace(',', '').strip())
                        except:
                            likes = 0
                        trend_items.append((i, label, likes))

                if trend_items:
                    print("\n" + create_ranking_list(trend_items, "TRENDING TWEETS", 70, show_bars=True))
                else:
                    info = [result[0].get('content', ''), result[0].get('metric', '')]
                    print(create_info_panel("ℹ️", "Information", info, 70))
            else:
                print(f"\n  {result}\n")

        print()


if __name__ == "__main__":
    main()
