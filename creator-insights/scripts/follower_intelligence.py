#!/usr/bin/env python3
"""
Follower Intelligence Module for Creator Insights
Engager-first approach: discovers who actually interacts with your content,
then enriches with follower status and influence scoring.
"""

import argparse
import sys
import json
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from api_client import APIClient
from ascii_formatter import (
    create_header, create_section_header, create_ranking_list,
    create_info_panel, format_number, colorize, Colors
)


class FollowerIntelligence:
    """Analyzes engagement and influence using an engager-first approach"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def analyze_vip_followers(self, username: str, num_tweets: int = 20,
                             max_followers: int = 500) -> Dict:
        """
        Discover who engages with your content and rank by influence.

        Pipeline: collect engagers from tweets → fetch followers for tagging →
        calculate influence scores → categorize.

        Args:
            username: Twitter username to analyze
            num_tweets: Number of recent tweets to analyze for engagement
            max_followers: Maximum followers to fetch for is_follower tagging

        Returns:
            Dict with engager analysis, hidden gems, and follower overlap
        """
        print(f"Analyzing engagement for @{username}...", file=sys.stderr)

        # Step 1: Fetch recent tweets
        print(f"Fetching last {num_tweets} tweets...", file=sys.stderr)
        tweets = self.api_client.get_twitter_user_timeline(username, num_tweets)
        if not tweets:
            return {"error": "Could not fetch tweets"}

        # Step 2: Collect all engagers (engager-first approach)
        print(f"Collecting engagers from {len(tweets)} tweets...", file=sys.stderr)
        engager_map = {}  # str(user_id) -> profile + engagement counts

        for i, tweet in enumerate(tweets[:num_tweets], 1):
            print(f"  Scanning tweet {i}/{min(num_tweets, len(tweets))}...", file=sys.stderr, end='\r')
            tweet_id = tweet["id"]

            # Get retweeters — each comes with full user profile
            retweeters = self.api_client.get_tweet_retweeters(tweet_id, max_results=100)
            for user in retweeters:
                uid = str(user["id"])
                if uid not in engager_map:
                    engager_map[uid] = {
                        "username": user["username"],
                        "name": user["name"],
                        "followers": user["followers"],
                        "verified": user["verified"],
                        "retweets": 0,
                        "replies": 0,
                        "total_interactions": 0
                    }
                engager_map[uid]["retweets"] += 1
                engager_map[uid]["total_interactions"] += 1

            # Get repliers — author data embedded in each reply
            replies = self.api_client.get_tweet_replies(tweet_id, max_results=100)
            for reply in replies:
                author = reply.get("author", {})
                uid = str(author.get("id"))
                if not uid or uid == "None":
                    continue
                if uid not in engager_map:
                    engager_map[uid] = {
                        "username": author.get("username", "Unknown"),
                        "name": author.get("name", "Unknown"),
                        "followers": author.get("followers", 0),
                        "verified": author.get("verified", False),
                        "retweets": 0,
                        "replies": 0,
                        "total_interactions": 0
                    }
                engager_map[uid]["replies"] += 1
                engager_map[uid]["total_interactions"] += 1

        print(f"\nFound {len(engager_map)} unique engagers", file=sys.stderr)

        if not engager_map:
            return {
                "username": username,
                "stats": {
                    "total_engagers": 0,
                    "engagers_who_follow": 0,
                    "unique_retweeters": 0,
                    "unique_repliers": 0
                },
                "message": "No engagers found on recent tweets. The account may have low engagement or tweets may be too new."
            }

        # Step 3: Fetch followers for is_follower tagging
        print(f"Fetching up to {max_followers} followers for follower tagging...", file=sys.stderr)
        followers = self.api_client.get_user_followers(username, max_followers)
        follower_ids = {str(f["id"]) for f in followers} if followers else set()

        # Step 4: Build results — score and categorize
        all_engagers = []
        for uid, data in engager_map.items():
            is_follower = uid in follower_ids
            influence_score = (data["followers"] * 0.7) + (data["total_interactions"] * 1000 * 0.3)

            all_engagers.append({
                "username": data["username"],
                "name": data["name"],
                "followers": data["followers"],
                "verified": data["verified"],
                "is_follower": is_follower,
                "engagement": {
                    "retweets": data["retweets"],
                    "replies": data["replies"],
                    "total_interactions": data["total_interactions"]
                },
                "influence_score": int(influence_score),
                "profile_url": f"https://twitter.com/{data['username']}"
            })

        # Sort by influence score
        all_engagers.sort(key=lambda x: x["influence_score"], reverse=True)

        # Calculate statistics
        total_engagers = len(all_engagers)
        engagers_who_follow = len([e for e in all_engagers if e["is_follower"]])
        unique_retweeters = len([uid for uid, d in engager_map.items() if d["retweets"] > 0])
        unique_repliers = len([uid for uid, d in engager_map.items() if d["replies"] > 0])

        return {
            "username": username,
            "stats": {
                "total_engagers": total_engagers,
                "engagers_who_follow": engagers_who_follow,
                "follow_rate": (engagers_who_follow / total_engagers * 100) if total_engagers > 0 else 0,
                "unique_retweeters": unique_retweeters,
                "unique_repliers": unique_repliers,
                "tweets_analyzed": min(num_tweets, len(tweets)),
                "followers_checked": len(follower_ids)
            },
            "top_engagers": all_engagers[:50],
            "hidden_gems": self._find_hidden_gems(all_engagers),
            "most_active": self._find_most_active(all_engagers),
            "follower_engagers": self._find_follower_engagers(all_engagers)
        }

    def _find_hidden_gems(self, engagers: List[Dict], max_followers: int = 5000) -> List[Dict]:
        """
        Find 'hidden gems' - engagers with low follower count but repeated engagement.

        Args:
            engagers: List of engager data
            max_followers: Maximum follower count to be considered a "gem"

        Returns:
            List of hidden gem engagers
        """
        gems = [
            e for e in engagers
            if e["followers"] < max_followers and e["engagement"]["total_interactions"] >= 2
        ]
        gems.sort(key=lambda x: x["engagement"]["total_interactions"], reverse=True)
        return gems[:10]

    def _find_most_active(self, engagers: List[Dict]) -> List[Dict]:
        """
        Find most active engagers by raw interaction count.

        Args:
            engagers: List of engager data

        Returns:
            List of most active engagers
        """
        active = sorted(engagers, key=lambda x: x["engagement"]["total_interactions"], reverse=True)
        return active[:20]

    def _find_follower_engagers(self, engagers: List[Dict]) -> List[Dict]:
        """
        Find engagers who are also followers — your most loyal audience.

        Args:
            engagers: List of engager data

        Returns:
            List of engagers who follow the account
        """
        follower_engagers = [e for e in engagers if e["is_follower"]]
        follower_engagers.sort(key=lambda x: x["influence_score"], reverse=True)
        return follower_engagers[:20]

    def analyze_follower_growth(self, username: str, sample_size: int = 200) -> Dict:
        """
        Analyze follower quality and growth patterns.

        Args:
            username: Twitter username
            sample_size: Number of recent followers to analyze

        Returns:
            Dict with follower growth analysis
        """
        print(f"Analyzing follower growth for @{username}...", file=sys.stderr)

        # Get recent followers (newest first)
        followers = self.api_client.get_user_followers(username, sample_size)
        if not followers:
            return {"error": "Could not fetch followers"}

        # Enrich follower profiles — the followers endpoint returns 0 for follower counts
        print(f"Enriching {len(followers)} follower profiles...", file=sys.stderr)
        follower_ids = [str(f["id"]) for f in followers if f.get("id")]
        # Batch in chunks of 100 (API pricing is better at 100+)
        for i in range(0, len(follower_ids), 100):
            chunk = follower_ids[i:i+100]
            enriched = self.api_client.batch_get_user_by_userids(chunk)
            if enriched:
                enriched_map = {str(u["id"]): u for u in enriched}
                for follower in followers:
                    uid = str(follower["id"])
                    if uid in enriched_map:
                        follower.update(enriched_map[uid])
                print(f"  Enriched batch {i//100 + 1} ({len(enriched)} profiles)", file=sys.stderr)

        # Analyze follower quality
        total_followers = len(followers)
        verified_count = len([f for f in followers if f["verified"]])
        avg_followers = sum(f["followers"] for f in followers) / total_followers if total_followers > 0 else 0

        # Categorize followers by size
        categories = {
            "micro": 0,    # < 1K
            "small": 0,    # 1K-10K
            "medium": 0,   # 10K-100K
            "large": 0,    # 100K-1M
            "mega": 0      # > 1M
        }

        for follower in followers:
            count = follower["followers"]
            if count < 1000:
                categories["micro"] += 1
            elif count < 10000:
                categories["small"] += 1
            elif count < 100000:
                categories["medium"] += 1
            elif count < 1000000:
                categories["large"] += 1
            else:
                categories["mega"] += 1

        return {
            "username": username,
            "total_analyzed": total_followers,
            "verified_followers": verified_count,
            "verified_percentage": (verified_count / total_followers * 100) if total_followers > 0 else 0,
            "avg_follower_count": int(avg_followers),
            "categories": categories,
            "category_percentages": {
                cat: (count / total_followers * 100) if total_followers > 0 else 0
                for cat, count in categories.items()
            },
            "recent_followers": followers[:20]
        }


def main():
    """CLI interface for Follower Intelligence"""
    parser = argparse.ArgumentParser(description="Analyze engagement and follower influence")
    parser.add_argument("--username", required=True, help="Twitter username to analyze (without @)")
    parser.add_argument("--tweets", type=int, default=20, help="Number of recent tweets to analyze for engagement")
    parser.add_argument("--max-followers", type=int, default=500, help="Maximum followers to fetch for tagging")
    parser.add_argument("--growth", action="store_true", help="Analyze follower growth and quality")
    parser.add_argument("--output", choices=['json', 'text'], default='text', help="Output format")

    args = parser.parse_args()

    # Initialize
    api_client = APIClient()
    analyzer = FollowerIntelligence(api_client)

    # Execute analysis
    if args.growth:
        result = analyzer.analyze_follower_growth(args.username, args.max_followers)
    else:
        result = analyzer.analyze_vip_followers(args.username, args.tweets, args.max_followers)

    # Output results
    if args.output == 'json':
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        if args.growth:
            # Follower growth analysis (unchanged)
            print(create_header(f"  FOLLOWER GROWTH: @{args.username}  ", 70))

            stats = [
                f"Total Analyzed: {colorize(str(result['total_analyzed']), Colors.BRIGHT_CYAN)}",
                f"Verified Followers: {colorize(str(result['verified_followers']), Colors.BRIGHT_GREEN)} ({result['verified_percentage']:.1f}%)",
                f"Avg Follower Count: {colorize(format_number(result['avg_follower_count']), Colors.BRIGHT_YELLOW)}"
            ]
            print(create_info_panel("📊", "Growth Statistics", stats, 70))

            print(create_section_header("👥 FOLLOWER CATEGORIES", 70))
            categories = result["categories"]
            category_items = []
            for i, (cat, count) in enumerate(categories.items(), 1):
                label = f"{cat.capitalize()} ({count} followers)"
                value = count
                category_items.append((i, label, value))

            print(create_ranking_list(category_items, "", 70, show_bars=True))

        else:
            # Engager-first analysis
            print(create_header(f"  ENGAGEMENT INTELLIGENCE: @{args.username}  ", 70))

            stats_data = result["stats"]
            stats = [
                f"Unique Engagers: {colorize(str(stats_data['total_engagers']), Colors.BRIGHT_CYAN)}",
                f"Retweeters: {colorize(str(stats_data['unique_retweeters']), Colors.BRIGHT_GREEN)}  |  Repliers: {colorize(str(stats_data['unique_repliers']), Colors.BRIGHT_GREEN)}",
                f"Engagers Who Follow: {colorize(str(stats_data['engagers_who_follow']), Colors.BRIGHT_YELLOW)} ({stats_data['follow_rate']:.1f}%)",
                f"Tweets Analyzed: {stats_data['tweets_analyzed']}  |  Followers Checked: {format_number(stats_data['followers_checked'])}"
            ]
            print(create_info_panel("📊", "Engagement Statistics", stats, 70))

            # Top engagers by influence
            if result["top_engagers"]:
                engager_items = []
                for i, engager in enumerate(result["top_engagers"][:10], 1):
                    verified_badge = "✓ " if engager["verified"] else ""
                    follow_badge = " [F]" if engager["is_follower"] else ""
                    label = f"{verified_badge}@{engager['username']}{follow_badge} ({format_number(engager['followers'])})"
                    value = engager["influence_score"]
                    engager_items.append((i, label, value))

                print("\n" + create_ranking_list(engager_items, "TOP ENGAGERS (BY INFLUENCE)", 70, show_bars=True))

                # Detail on #1 engager
                top = result["top_engagers"][0]
                follow_text = "follows you" if top["is_follower"] else "does not follow you"
                print(f"\n  {'Top Engager Details:':^70}")
                print(f"  {'-' * 68}")
                top_username = top["username"]
                print(f"  👤 {colorize(f'@{top_username}', Colors.BRIGHT_CYAN)} ({top['name']})")
                print(f"  👥 Followers: {colorize(format_number(top['followers']), Colors.BRIGHT_GREEN)}  |  {follow_text}")
                eng = top["engagement"]
                print(f"  💬 {eng['retweets']} RTs | {eng['replies']} replies | {eng['total_interactions']} total")
                print(f"  🏆 Influence Score: {colorize(format_number(top['influence_score']), Colors.BRIGHT_YELLOW)}")

            # Hidden gems
            if result["hidden_gems"]:
                print(create_section_header("💎 HIDDEN GEMS (High Engagement, Low Followers)", 70))
                gem_items = []
                for i, gem in enumerate(result["hidden_gems"][:5], 1):
                    follow_badge = " [F]" if gem["is_follower"] else ""
                    label = f"@{gem['username']}{follow_badge} ({format_number(gem['followers'])})"
                    value = gem["engagement"]["total_interactions"] * 100
                    gem_items.append((i, label, value))

                print(create_ranking_list(gem_items, "", 70, show_bars=True))

            # Most active
            if result["most_active"]:
                print(create_section_header("🔥 MOST ACTIVE (By Interactions)", 70))
                for i, engager in enumerate(result["most_active"][:5], 1):
                    eng = engager["engagement"]
                    follow_badge = " [F]" if engager["is_follower"] else ""
                    print(f"  {i}. @{engager['username']}{follow_badge}")
                    print(f"     {eng['retweets']} RTs | {eng['replies']} replies | {eng['total_interactions']} total")

            # Follower engagers
            if result["follower_engagers"]:
                print(create_section_header("🤝 LOYAL FOLLOWERS (Follow + Engage)", 70))
                for i, engager in enumerate(result["follower_engagers"][:5], 1):
                    eng = engager["engagement"]
                    verified_badge = "✓ " if engager["verified"] else ""
                    print(f"  {i}. {verified_badge}@{engager['username']} ({format_number(engager['followers'])} followers)")
                    print(f"     {eng['total_interactions']} interactions | Influence: {format_number(engager['influence_score'])}")

        print()


if __name__ == "__main__":
    main()
