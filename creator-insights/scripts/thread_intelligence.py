#!/usr/bin/env python3
"""
Thread Intelligence Module for Creator Insights
Identifies threads and analyzes high-value engagement from influential accounts.
"""

import argparse
import sys
import json
from typing import Dict, List, Optional
from collections import defaultdict
from api_client import APIClient
from ascii_formatter import (
    create_header, create_section_header, create_ranking_list,
    create_info_panel, format_number, colorize, Colors
)


class ThreadIntelligence:
    """Analyzes Twitter threads and high-value engagement"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def analyze_threads(self, username: str, num_tweets: int = 50,
                       high_value_threshold: int = 10000) -> Dict:
        """
        Identify threads and analyze replies from high-value accounts.

        Args:
            username: Twitter username to analyze
            num_tweets: Number of recent tweets to analyze
            high_value_threshold: Minimum follower count to be "high-value" (default: 10K)

        Returns:
            Dict with thread analysis
        """
        print(f"Analyzing threads for @{username}...", file=sys.stderr)

        # Step 1: Get user's timeline
        print(f"Fetching last {num_tweets} tweets...", file=sys.stderr)
        tweets = self.api_client.get_twitter_user_timeline(username, num_tweets, include_replies=False)
        if not tweets:
            return {"error": "Could not fetch tweets"}

        # Step 2: Identify threads (tweets that are part of a conversation)
        print(f"Identifying threads...", file=sys.stderr)
        threads = self._identify_threads(tweets)

        if not threads:
            return {
                "username": username,
                "threads_found": 0,
                "message": "No threads found in recent tweets. Note: threads are detected as Twitter reply chains (2+ tweets linked via conversation_id). Creators who post standalone updates rather than threaded chains will naturally show few/no threads — this reflects posting style, not a lack of content."
            }

        print(f"Found {len(threads)} threads", file=sys.stderr)

        # Step 3: Analyze replies for each thread
        print(f"Analyzing replies from high-value accounts...", file=sys.stderr)
        thread_analysis = []

        for i, thread in enumerate(threads[:20], 1):  # Analyze top 20 threads
            print(f"  Thread {i}/{min(20, len(threads))}...", file=sys.stderr, end='\r')

            # Get thread context (all tweets in thread)
            thread_tweets = self.api_client.get_tweet_thread_context(thread["first_tweet_id"], max_results=50)

            # Get replies to the thread starter
            replies = self.api_client.get_tweet_replies(thread["first_tweet_id"], max_results=50)

            # Analyze high-value repliers
            high_value_replies = []
            total_reply_engagement = 0

            for reply in replies:
                author = reply.get("author", {})
                follower_count = author.get("followers", 0)

                reply_engagement = reply["likes"] + reply["retweets"] + reply["replies"]
                total_reply_engagement += reply_engagement

                if follower_count >= high_value_threshold:
                    high_value_replies.append({
                        "username": author.get("username", "Unknown"),
                        "name": author.get("name", "Unknown"),
                        "followers": follower_count,
                        "verified": author.get("verified", False),
                        "reply_text": reply["text"][:100],
                        "reply_engagement": reply_engagement
                    })

            # Sort high-value replies by follower count
            high_value_replies.sort(key=lambda x: x["followers"], reverse=True)

            thread_analysis.append({
                "thread_id": thread["first_tweet_id"],
                "first_tweet_text": thread["first_tweet_text"],
                "first_tweet_url": thread["first_tweet_url"],
                "tweet_count": len(thread_tweets) if thread_tweets else thread["tweet_count"],
                "total_replies": len(replies),
                "total_reply_engagement": total_reply_engagement,
                "high_value_replies": high_value_replies,
                "high_value_count": len(high_value_replies),
                "avg_replier_followers": sum(r["followers"] for r in high_value_replies) / len(high_value_replies) if high_value_replies else 0,
                "total_engagement": thread["total_engagement"]
            })

        print(f"\nThread analysis complete!", file=sys.stderr)

        # Sort threads by high-value reply count
        thread_analysis.sort(key=lambda x: x["high_value_count"], reverse=True)

        # Calculate statistics
        total_threads = len(thread_analysis)
        threads_with_high_value = len([t for t in thread_analysis if t["high_value_count"] > 0])
        total_high_value_replies = sum(t["high_value_count"] for t in thread_analysis)
        total_replies = sum(t["total_replies"] for t in thread_analysis)

        # Add warning if no engagement found
        warning = None
        if total_replies == 0:
            warning = "No replies found on recent threads. This may indicate low engagement, content without responses, or an account with limited interaction."
        elif total_high_value_replies == 0 and total_replies > 0:
            warning = f"No high-value replies found (threshold: {high_value_threshold:,} followers). Try lowering --threshold or the account may not attract influential engagement yet."

        return {
            "username": username,
            "stats": {
                "total_threads": total_threads,
                "threads_with_high_value_replies": threads_with_high_value,
                "total_high_value_replies": total_high_value_replies,
                "total_replies": total_replies,
                "high_value_threshold": high_value_threshold,
                "engagement_rate": (threads_with_high_value / total_threads * 100) if total_threads > 0 else 0
            },
            "warning": warning,
            "threads": thread_analysis[:20],  # Top 20 threads
            "top_repliers": self._find_top_repliers(thread_analysis)
        }

    def _identify_threads(self, tweets: List[Dict]) -> List[Dict]:
        """
        Identify threads from timeline using conversation_id.

        Twitter's conversation_id groups all tweets in a thread together.
        A thread is any tweet/conversation that may have replies.

        Args:
            tweets: List of tweet objects

        Returns:
            List of thread objects with metadata
        """
        threads = []

        # Group tweets by conversation_id (Twitter's native thread identifier)
        conversations = defaultdict(list)
        for tweet in tweets:
            # Use conversation_id if available, otherwise treat as standalone
            conversation_id = tweet.get("conversation_id") or tweet["id"]
            conversations[conversation_id].append(tweet)

        # Create thread objects — only include conversations with 2+ tweets
        for conversation_id, tweet_list in conversations.items():
            if len(tweet_list) < 2:
                continue

            # Sort by created_at to find first tweet
            tweet_list.sort(key=lambda t: t.get("created_at", ""), reverse=False)
            first_tweet = tweet_list[0]

            # Calculate total engagement for the thread
            total_engagement = sum(
                t["likes"] + t["retweets"] + t["replies"]
                for t in tweet_list
            )

            threads.append({
                "first_tweet_id": first_tweet["id"],
                "first_tweet_text": first_tweet["text"][:150],
                "first_tweet_url": first_tweet["url"],
                "conversation_id": conversation_id,
                "tweet_count": len(tweet_list),
                "total_engagement": total_engagement,
                "created_at": first_tweet.get("created_at")
            })

        # Sort by engagement
        threads.sort(key=lambda x: x["total_engagement"], reverse=True)

        return threads

    def _find_top_repliers(self, thread_analysis: List[Dict]) -> List[Dict]:
        """
        Find the most frequent high-value repliers across all threads.

        Args:
            thread_analysis: List of thread analysis data

        Returns:
            List of top repliers
        """
        replier_stats = defaultdict(lambda: {
            "reply_count": 0,
            "total_followers": 0,
            "threads_engaged": set()
        })

        for thread in thread_analysis:
            for reply in thread.get("high_value_replies", []):
                username = reply["username"]
                replier_stats[username]["reply_count"] += 1
                replier_stats[username]["total_followers"] = reply["followers"]
                replier_stats[username]["name"] = reply["name"]
                replier_stats[username]["verified"] = reply["verified"]
                replier_stats[username]["threads_engaged"].add(thread["thread_id"])

        # Convert to list and sort by reply count
        top_repliers = []
        for username, stats in replier_stats.items():
            top_repliers.append({
                "username": username,
                "name": stats["name"],
                "followers": stats["total_followers"],
                "verified": stats["verified"],
                "reply_count": stats["reply_count"],
                "threads_engaged": len(stats["threads_engaged"])
            })

        top_repliers.sort(key=lambda x: x["reply_count"], reverse=True)

        return top_repliers[:10]  # Top 10 repliers

    def compare_thread_performance(self, username: str, num_tweets: int = 50) -> Dict:
        """
        Compare threads vs standalone tweets performance.

        Args:
            username: Twitter username
            num_tweets: Number of tweets to analyze

        Returns:
            Comparison analysis
        """
        print(f"Comparing thread vs standalone performance for @{username}...", file=sys.stderr)

        tweets = self.api_client.get_twitter_user_timeline(username, num_tweets)
        if not tweets:
            return {"error": "Could not fetch tweets"}

        # Use _identify_threads to find which tweets belong to threads (2+ tweet chains)
        identified_threads = self._identify_threads(tweets)
        thread_tweet_ids = set()
        for thread in identified_threads:
            thread_tweet_ids.add(thread["conversation_id"])

        threads = []
        standalone = []

        for tweet in tweets:
            engagement = tweet["likes"] + tweet["retweets"] + tweet["replies"]
            conv_id = tweet.get("conversation_id") or tweet["id"]

            if conv_id in thread_tweet_ids:
                threads.append({
                    "engagement": engagement,
                    "text": tweet["text"][:100],
                    "url": tweet["url"]
                })
            else:
                standalone.append({
                    "engagement": engagement,
                    "text": tweet["text"][:100],
                    "url": tweet["url"]
                })

        # Calculate averages
        avg_thread_engagement = sum(t["engagement"] for t in threads) / len(threads) if threads else 0
        avg_standalone_engagement = sum(t["engagement"] for t in standalone) / len(standalone) if standalone else 0

        return {
            "username": username,
            "threads": {
                "count": len(threads),
                "avg_engagement": avg_thread_engagement,
                "top_threads": sorted(threads, key=lambda x: x["engagement"], reverse=True)[:5]
            },
            "standalone": {
                "count": len(standalone),
                "avg_engagement": avg_standalone_engagement,
                "top_standalone": sorted(standalone, key=lambda x: x["engagement"], reverse=True)[:5]
            },
            "comparison": {
                "threads_perform_better": avg_thread_engagement > avg_standalone_engagement,
                "performance_difference": ((avg_thread_engagement / avg_standalone_engagement) - 1) * 100 if avg_standalone_engagement > 0 else 0
            }
        }


def main():
    """CLI interface for Thread Intelligence"""
    parser = argparse.ArgumentParser(description="Analyze Twitter threads and high-value engagement")
    parser.add_argument("--username", required=True, help="Twitter username to analyze (without @)")
    parser.add_argument("--tweets", type=int, default=50, help="Number of recent tweets to analyze")
    parser.add_argument("--threshold", type=int, default=10000, help="High-value follower threshold (default: 10K)")
    parser.add_argument("--compare", action="store_true", help="Compare threads vs standalone performance")
    parser.add_argument("--output", choices=['json', 'text'], default='text', help="Output format")

    args = parser.parse_args()

    # Initialize
    api_client = APIClient()
    analyzer = ThreadIntelligence(api_client)

    # Execute analysis
    if args.compare:
        result = analyzer.compare_thread_performance(args.username, args.tweets)
    else:
        result = analyzer.analyze_threads(args.username, args.tweets, args.threshold)

    # Output results
    if args.output == 'json':
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        # Format text output with ASCII art
        if args.compare:
            # Thread comparison
            print(create_header(f"  THREAD PERFORMANCE: @{args.username}  ", 70))

            threads_data = result["threads"]
            standalone_data = result["standalone"]
            comparison = result["comparison"]

            stats = [
                f"Threads: {colorize(str(threads_data['count']), Colors.BRIGHT_CYAN)} (avg: {format_number(threads_data['avg_engagement'])} engagement)",
                f"Standalone: {colorize(str(standalone_data['count']), Colors.BRIGHT_YELLOW)} (avg: {format_number(standalone_data['avg_engagement'])} engagement)",
                f"Performance: {colorize('Threads win!' if comparison['threads_perform_better'] else 'Standalone wins!', Colors.BRIGHT_GREEN)}"
            ]
            print(create_info_panel("📊", "Performance Comparison", stats, 70))

            if comparison["threads_perform_better"]:
                print(f"\n  🎯 Threads perform {comparison['performance_difference']:.1f}% better!")
                print(f"  💡 Recommendation: Create more threads to maximize engagement")
            else:
                print(f"\n  🎯 Standalone tweets perform better")
                print(f"  💡 Recommendation: Focus on impactful single tweets")

        else:
            # Thread intelligence
            print(create_header(f"  THREAD INTELLIGENCE: @{args.username}  ", 70))

            stats_data = result["stats"]
            stats = [
                f"Total Threads: {colorize(str(stats_data['total_threads']), Colors.BRIGHT_CYAN)}",
                f"With High-Value Replies: {colorize(str(stats_data['threads_with_high_value_replies']), Colors.BRIGHT_GREEN)} ({stats_data['engagement_rate']:.1f}%)",
                f"Total High-Value Replies: {colorize(str(stats_data['total_high_value_replies']), Colors.BRIGHT_YELLOW)}",
                f"Threshold: {format_number(stats_data['high_value_threshold'])} followers"
            ]
            print(create_info_panel("📊", "Thread Statistics", stats, 70))

            # Top threads by high-value engagement
            thread_items = []
            for i, thread in enumerate(result["threads"][:10], 1):
                label = f"{thread['first_tweet_text'][:35]}... ({thread['tweet_count']} tweets)"
                value = thread['high_value_count'] * 1000  # Scale for visualization
                thread_items.append((i, label, value))

            print("\n" + create_ranking_list(thread_items, "TOP THREADS (BY HIGH-VALUE REPLIES)", 70, show_bars=True))

            # Show details of top thread
            if result["threads"]:
                top_thread = result["threads"][0]
                print(f"\n  {'Top Thread Details:':^70}")
                print(f"  {'-' * 68}")
                print(f"  💬 {top_thread['first_tweet_text'][:60]}")
                print(f"  🧵 Thread Length: {top_thread['tweet_count']} tweets")
                print(f"  💭 Total Replies: {top_thread['total_replies']}")
                print(f"  ⭐ High-Value Replies: {colorize(str(top_thread['high_value_count']), Colors.BRIGHT_YELLOW)}")
                print(f"  📈 Reply Engagement: {colorize(format_number(top_thread['total_reply_engagement']), Colors.BRIGHT_GREEN)}")

                # Show top repliers for this thread
                if top_thread["high_value_replies"]:
                    print(f"\n  Top High-Value Repliers:")
                    for replier in top_thread["high_value_replies"][:3]:
                        verified_badge = "✓ " if replier["verified"] else ""
                        print(f"    {verified_badge}@{replier['username']} ({format_number(replier['followers'])} followers)")

            # Top repliers across all threads
            if result.get("top_repliers"):
                print(create_section_header("🏆 MOST ENGAGED HIGH-VALUE ACCOUNTS", 70))
                for i, replier in enumerate(result["top_repliers"][:5], 1):
                    verified_badge = "✓ " if replier["verified"] else ""
                    print(f"  {i}. {verified_badge}@{replier['username']} ({format_number(replier['followers'])} followers)")
                    print(f"     {replier['reply_count']} replies across {replier['threads_engaged']} threads")

        print()


if __name__ == "__main__":
    main()
