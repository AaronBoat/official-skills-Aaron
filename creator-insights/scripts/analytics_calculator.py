#!/usr/bin/env python3
"""
Analytics Calculator for Creator Insights
Calculates posting cadence, engagement rates, and performance metrics.
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from api_client import APIClient


class AnalyticsCalculator:
    """Calculates content performance analytics"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def calculate_metrics(self, profile: str, platform: str, timeframe: str = "30d") -> Dict:
        """
        Calculate comprehensive analytics for a creator's profile.

        Args:
            profile: Username or profile URL
            platform: Social media platform
            timeframe: Analysis period (7d, 30d, 90d)

        Returns:
            Dict with posting cadence, engagement, and performance metrics
        """
        print(f"Calculating analytics for @{profile} on {platform}...", file=sys.stderr)

        # Parse timeframe
        days = self._parse_timeframe(timeframe)

        # Fetch posts within timeframe
        posts = self._fetch_posts(platform, profile, days)

        if not posts:
            return {
                "error": "No posts found or unable to fetch data",
                "suggestion": "Check API configuration or provide a different profile"
            }

        # Calculate all metrics
        metrics = {
            "profile": profile,
            "platform": platform,
            "timeframe": timeframe,
            "analysis_date": datetime.now().isoformat(),
            "posting_cadence": self._calculate_posting_cadence(posts, days),
            "engagement_metrics": self._calculate_engagement_metrics(posts),
            "content_performance": self._analyze_content_performance(posts),
            "growth_metrics": self._calculate_growth_metrics(posts),
            "audience_insights": self._analyze_audience_behavior(posts),
            "recommendations": self._generate_recommendations(posts, days)
        }

        return metrics

    def _parse_timeframe(self, timeframe: str) -> int:
        """Convert timeframe string to number of days"""
        mapping = {
            "7d": 7,
            "30d": 30,
            "90d": 90,
            "1w": 7,
            "1m": 30,
            "3m": 90
        }
        return mapping.get(timeframe.lower(), 30)

    def _fetch_posts(self, platform: str, username: str, days: int) -> List[Dict]:
        """Fetch posts from the specified timeframe"""
        # This would fetch actual posts from the API
        # For now, return a structure that scripts can populate
        posts = []

        # Example structure (to be populated by real API calls):
        # posts.append({
        #     "id": "post123",
        #     "timestamp": datetime.now().isoformat(),
        #     "type": "video",
        #     "likes": 1500,
        #     "comments": 89,
        #     "shares": 45,
        #     "views": 25000,
        #     "caption": "Check out this tutorial...",
        #     "hashtags": ["#tutorial", "#howto"]
        # })

        print(f"Note: Fetching real post data requires API authentication", file=sys.stderr)

        return posts

    def _calculate_posting_cadence(self, posts: List[Dict], days: int) -> Dict:
        """Calculate posting frequency and consistency"""
        if not posts:
            return {"frequency": "no data", "consistency_score": 0}

        post_count = len(posts)
        posts_per_week = (post_count / days) * 7

        # Calculate consistency score (0-10)
        # Based on regularity of posting
        if post_count >= 2:
            # Calculate time gaps between posts
            timestamps = []
            for post in posts:
                if "timestamp" in post:
                    try:
                        ts = datetime.fromisoformat(post["timestamp"].replace('Z', '+00:00'))
                        timestamps.append(ts)
                    except:
                        pass

            if len(timestamps) >= 2:
                timestamps.sort()
                gaps = [(timestamps[i+1] - timestamps[i]).days for i in range(len(timestamps)-1)]
                avg_gap = sum(gaps) / len(gaps) if gaps else 0
                gap_variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps) if gaps else 0

                # Lower variance = higher consistency
                consistency_score = max(0, 10 - (gap_variance ** 0.5))
            else:
                consistency_score = 5.0  # Default for insufficient data
        else:
            consistency_score = 0

        # Determine frequency category
        if posts_per_week >= 7:
            frequency = "Daily (7+ posts/week)"
        elif posts_per_week >= 3:
            frequency = "Very Active (3-6 posts/week)"
        elif posts_per_week >= 1:
            frequency = "Active (1-2 posts/week)"
        else:
            frequency = "Occasional (<1 post/week)"

        return {
            "total_posts": post_count,
            "posts_per_week": round(posts_per_week, 1),
            "frequency": frequency,
            "consistency_score": round(consistency_score, 1),
            "days_analyzed": days
        }

    def _calculate_engagement_metrics(self, posts: List[Dict]) -> Dict:
        """Calculate engagement rates and metrics"""
        if not posts:
            return {"error": "no data"}

        total_likes = sum(post.get("likes", 0) for post in posts)
        total_comments = sum(post.get("comments", 0) for post in posts)
        total_shares = sum(post.get("shares", 0) for post in posts)
        total_views = sum(post.get("views", 0) for post in posts)

        avg_likes = total_likes / len(posts) if posts else 0
        avg_comments = total_comments / len(posts) if posts else 0
        avg_shares = total_shares / len(posts) if posts else 0
        avg_views = total_views / len(posts) if posts else 0

        # Calculate engagement rate
        # Engagement rate = (likes + comments + shares) / views * 100
        total_engagement = total_likes + total_comments + total_shares
        engagement_rate = (total_engagement / total_views * 100) if total_views > 0 else 0

        return {
            "total_engagement": total_engagement,
            "engagement_rate": round(engagement_rate, 2),
            "average_likes": round(avg_likes, 1),
            "average_comments": round(avg_comments, 1),
            "average_shares": round(avg_shares, 1),
            "average_views": round(avg_views, 1),
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_views": total_views
        }

    def _analyze_content_performance(self, posts: List[Dict]) -> Dict:
        """Analyze which content performs best"""
        if not posts:
            return {"error": "no data"}

        # Group by content type
        type_performance = defaultdict(lambda: {"count": 0, "total_engagement": 0})

        for post in posts:
            content_type = post.get("type", "unknown")
            engagement = post.get("likes", 0) + post.get("comments", 0) + post.get("shares", 0)

            type_performance[content_type]["count"] += 1
            type_performance[content_type]["total_engagement"] += engagement

        # Calculate averages
        type_averages = {}
        for ctype, data in type_performance.items():
            avg_engagement = data["total_engagement"] / data["count"] if data["count"] > 0 else 0
            type_averages[ctype] = {
                "count": data["count"],
                "avg_engagement": round(avg_engagement, 1)
            }

        # Find best performing type
        best_type = max(type_averages.items(), key=lambda x: x[1]["avg_engagement"]) if type_averages else ("none", {})

        # Find top performing posts
        top_posts = sorted(posts, key=lambda p: p.get("likes", 0) + p.get("comments", 0) + p.get("shares", 0),
                          reverse=True)[:3]

        top_content = []
        for post in top_posts:
            engagement = post.get("likes", 0) + post.get("comments", 0) + post.get("shares", 0)
            engagement_rate = (engagement / post.get("views", 1) * 100) if post.get("views", 0) > 0 else 0

            top_content.append({
                "type": post.get("type", "unknown"),
                "caption": post.get("caption", "")[:50] + "..." if len(post.get("caption", "")) > 50 else post.get("caption", ""),
                "engagement": engagement,
                "engagement_rate": round(engagement_rate, 2),
                "likes": post.get("likes", 0),
                "comments": post.get("comments", 0)
            })

        return {
            "content_types": type_averages,
            "best_performing_type": best_type[0],
            "top_content": top_content
        }

    def _calculate_growth_metrics(self, posts: List[Dict]) -> Dict:
        """Calculate growth and reach metrics"""
        if not posts:
            return {"error": "no data"}

        # This would require historical follower data
        # For now, provide structure for growth analysis

        # Calculate reach trend (if view data available)
        if all("views" in post for post in posts):
            recent_views = sum(post["views"] for post in posts[:len(posts)//2])
            older_views = sum(post["views"] for post in posts[len(posts)//2:])

            if older_views > 0:
                views_change = ((recent_views - older_views) / older_views) * 100
            else:
                views_change = 0
        else:
            views_change = 0

        return {
            "reach_trend": f"{'+' if views_change > 0 else ''}{round(views_change, 1)}%",
            "reach_status": "growing" if views_change > 10 else "stable" if views_change > -10 else "declining",
            "note": "Growth metrics require historical follower data"
        }

    def _analyze_audience_behavior(self, posts: List[Dict]) -> Dict:
        """Analyze when audience is most active"""
        if not posts:
            return {"error": "no data"}

        # Analyze posting times and correlate with engagement
        time_engagement = defaultdict(lambda: {"posts": 0, "total_engagement": 0})

        for post in posts:
            if "timestamp" not in post:
                continue

            try:
                ts = datetime.fromisoformat(post["timestamp"].replace('Z', '+00:00'))
                hour = ts.hour
                day = ts.strftime("%A")

                # Categorize by time of day
                if 6 <= hour < 12:
                    time_period = "morning"
                elif 12 <= hour < 17:
                    time_period = "afternoon"
                elif 17 <= hour < 21:
                    time_period = "evening"
                else:
                    time_period = "night"

                engagement = post.get("likes", 0) + post.get("comments", 0) + post.get("shares", 0)

                time_engagement[time_period]["posts"] += 1
                time_engagement[time_period]["total_engagement"] += engagement
            except:
                pass

        # Calculate best times
        best_time = "afternoon/evening"  # Default
        if time_engagement:
            best_time = max(time_engagement.items(),
                          key=lambda x: x[1]["total_engagement"] / x[1]["posts"] if x[1]["posts"] > 0 else 0)[0]

        return {
            "best_posting_time": best_time,
            "time_breakdown": dict(time_engagement),
            "recommendation": f"Post during {best_time} for best engagement"
        }

    def _generate_recommendations(self, posts: List[Dict], days: int) -> List[str]:
        """Generate actionable recommendations based on analytics"""
        recommendations = []

        if not posts:
            return ["Unable to generate recommendations without post data"]

        post_count = len(posts)
        posts_per_week = (post_count / days) * 7

        # Posting frequency recommendations
        if posts_per_week < 1:
            recommendations.append("Increase posting frequency to at least 1-2 posts per week for better reach")
        elif posts_per_week > 10:
            recommendations.append("Consider reducing posting frequency to focus on quality over quantity")

        # Engagement recommendations
        engagement_metrics = self._calculate_engagement_metrics(posts)
        if engagement_metrics.get("engagement_rate", 0) < 2:
            recommendations.append("Engagement rate is below average - try more interactive content (polls, questions, calls-to-action)")

        # Content type recommendations
        content_perf = self._analyze_content_performance(posts)
        if content_perf.get("best_performing_type") and content_perf["best_performing_type"] != "unknown":
            recommendations.append(f"Focus more on {content_perf['best_performing_type']} content - it performs best for your audience")

        # General recommendations
        recommendations.append("Analyze trending content in your niche and adapt successful patterns")
        recommendations.append("Engage with your audience by responding to comments promptly")

        return recommendations


def main():
    """CLI interface for Twitter analytics calculator"""
    parser = argparse.ArgumentParser(description="Calculate Twitter analytics and metrics")
    parser.add_argument("--profile", required=True, help="Twitter username or URL")
    parser.add_argument("--timeframe", default="30d",
                       choices=["7d", "30d", "90d"],
                       help="Analysis timeframe")
    parser.add_argument("--output", choices=['json', 'text'], default='text',
                       help="Output format")

    args = parser.parse_args()

    # Initialize API client and calculator
    api_client = APIClient()
    calculator = AnalyticsCalculator(api_client)

    # Calculate metrics
    result = calculator.calculate_metrics(args.profile, "twitter", args.timeframe)

    # Output results
    if args.output == 'json':
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            if "suggestion" in result:
                print(f"Suggestion: {result['suggestion']}", file=sys.stderr)
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"TWITTER ANALYTICS: @{result['profile']}")
        print(f"Timeframe: {result['timeframe']}")
        print(f"{'='*60}\n")

        # Posting Cadence
        cadence = result["posting_cadence"]
        print("POSTING CADENCE")
        print("-" * 40)
        print(f"Total Posts: {cadence['total_posts']}")
        print(f"Posts per Week: {cadence['posts_per_week']}")
        print(f"Frequency: {cadence['frequency']}")
        print(f"Consistency Score: {cadence['consistency_score']}/10\n")

        # Engagement Metrics
        engagement = result["engagement_metrics"]
        if "error" not in engagement:
            print("ENGAGEMENT METRICS")
            print("-" * 40)
            print(f"Engagement Rate: {engagement['engagement_rate']}%")
            print(f"Average Likes: {engagement['average_likes']}")
            print(f"Average Comments: {engagement['average_comments']}")
            print(f"Average Shares: {engagement['average_shares']}")
            print(f"Average Views: {engagement['average_views']}\n")

        # Content Performance
        performance = result["content_performance"]
        if "error" not in performance:
            print("CONTENT PERFORMANCE")
            print("-" * 40)
            print(f"Best Performing Type: {performance['best_performing_type']}")
            print("\nTop Content:")
            for i, content in enumerate(performance['top_content'], 1):
                print(f"{i}. {content['caption']}")
                print(f"   Type: {content['type']} | Engagement: {content['engagement']} ({content['engagement_rate']}%)")
            print()

        # Audience Insights
        audience = result["audience_insights"]
        if "error" not in audience:
            print("AUDIENCE INSIGHTS")
            print("-" * 40)
            print(f"Best Posting Time: {audience['best_posting_time']}")
            print(f"Recommendation: {audience['recommendation']}\n")

        # Recommendations
        print("RECOMMENDATIONS")
        print("-" * 40)
        for i, rec in enumerate(result["recommendations"], 1):
            print(f"{i}. {rec}")
        print()


if __name__ == "__main__":
    main()
