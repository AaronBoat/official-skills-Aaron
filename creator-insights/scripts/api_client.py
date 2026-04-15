#!/usr/bin/env python3
"""
Twitter API Client for Creator Insights
Provides access to Twitter/X data via TwitterAPI.io.
"""

import os
import sys
import json
import time
import requests
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta

class APIClient:
    """Twitter API client using TwitterAPI.io via sc-proxy"""

    def __init__(self):
        """
        Initialize API client.

        Requires TWITTER_API_KEY environment variable.
        Uses proxied HTTP client for billing/tracking through sc-proxy.
        """
        self.api_key = os.environ.get("TWITTER_API_KEY", "")
        if not self.api_key:
            print("Warning: TWITTER_API_KEY not set in environment", file=sys.stderr)

        # Rate limiting tracking
        self.rate_limits = {}

    # ============== Date Filtering Helpers ==============

    @staticmethod
    def parse_relative_date(relative_str: str) -> datetime:
        """
        Parse relative date strings like '24h', '7d', 'this week' into datetime.

        Args:
            relative_str: Relative date string (24h, 7d, 30d, this week, this month)

        Returns:
            datetime object

        Examples:
            '24h' -> 24 hours ago
            '7d' -> 7 days ago
            'this week' -> Monday of this week at 00:00
        """
        now = datetime.now()

        # Handle hour format: 24h, 48h
        if relative_str.endswith('h'):
            hours = int(relative_str[:-1])
            return now - timedelta(hours=hours)

        # Handle day format: 7d, 30d
        if relative_str.endswith('d'):
            days = int(relative_str[:-1])
            return now - timedelta(days=days)

        # Handle week format: 1w, 2w
        if relative_str.endswith('w'):
            weeks = int(relative_str[:-1])
            return now - timedelta(weeks=weeks)

        # Handle special keywords
        if relative_str.lower() == 'today':
            return now.replace(hour=0, minute=0, second=0, microsecond=0)

        if relative_str.lower() in ['this week', 'week']:
            # Go to Monday of this week
            days_since_monday = now.weekday()
            return (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)

        if relative_str.lower() in ['this month', 'month']:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # If it's a date string, try parsing it
        try:
            return datetime.fromisoformat(relative_str)
        except:
            pass

        # Default: 24 hours ago
        return now - timedelta(hours=24)

    @staticmethod
    def format_twitter_date(dt: datetime, timezone: str = "UTC") -> str:
        """
        Format datetime for Twitter advanced search (since: / until: operators).

        Args:
            dt: datetime object
            timezone: Timezone abbreviation (default: UTC)

        Returns:
            Formatted string: "YYYY-MM-DD_HH:MM:SS_UTC"

        Example:
            datetime(2025, 3, 29, 12, 0, 0) -> "2025-03-29_12:00:00_UTC"
        """
        return dt.strftime(f"%Y-%m-%d_%H:%M:%S_{timezone}")

    @staticmethod
    def build_time_filtered_query(base_query: str, since: Optional[str] = None,
                                  until: Optional[str] = None) -> str:
        """
        Build Twitter search query with time filters.

        Args:
            base_query: Base search terms (e.g., "AI" OR "machine learning")
            since: Since date/time (relative or absolute)
            until: Until date/time (relative or absolute)

        Returns:
            Query string with since:/until: operators

        Examples:
            ("AI", "24h", None) -> "AI since:2025-03-29_12:00:00_UTC"
            ("crypto", "7d", "today") -> "crypto since:2025-03-22_00:00:00_UTC until:2025-03-30_00:00:00_UTC"
        """
        query_parts = [base_query]

        if since:
            since_dt = APIClient.parse_relative_date(since)
            since_formatted = APIClient.format_twitter_date(since_dt)
            query_parts.append(f"since:{since_formatted}")

        if until:
            until_dt = APIClient.parse_relative_date(until)
            until_formatted = APIClient.format_twitter_date(until_dt)
            query_parts.append(f"until:{until_formatted}")

        return " ".join(query_parts)

    @staticmethod
    def filter_tweets_by_date(tweets: List[Dict], since: Optional[str] = None,
                             until: Optional[str] = None) -> List[Dict]:
        """
        Filter tweets by date range (client-side filtering).

        Args:
            tweets: List of tweet objects with 'created_at' field
            since: Since date/time (relative or absolute)
            until: Until date/time (relative or absolute)

        Returns:
            Filtered list of tweets
        """
        if not since and not until:
            return tweets

        since_dt = APIClient.parse_relative_date(since) if since else datetime.min
        until_dt = APIClient.parse_relative_date(until) if until else datetime.max

        filtered = []
        for tweet in tweets:
            created_at_str = tweet.get("created_at")
            if not created_at_str:
                continue

            try:
                # Parse Twitter date format
                tweet_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                # Remove timezone info for comparison
                tweet_dt = tweet_dt.replace(tzinfo=None)

                if since_dt <= tweet_dt <= until_dt:
                    filtered.append(tweet)
            except:
                # If date parsing fails, include the tweet
                filtered.append(tweet)

        return filtered

    # ============== HTTP Client ==============

    def _check_rate_limit(self, platform: str) -> bool:
        """Check if we're within rate limits for a platform"""
        if platform not in self.rate_limits:
            return True

        last_call, calls_count = self.rate_limits[platform]
        current_time = time.time()

        # Reset counter after 60 seconds
        if current_time - last_call > 60:
            self.rate_limits[platform] = (current_time, 1)
            return True

        # Most APIs allow ~100-300 calls per minute
        if calls_count >= 100:
            print(f"Rate limit reached for {platform}. Waiting...", file=sys.stderr)
            time.sleep(60 - (current_time - last_call))
            self.rate_limits[platform] = (time.time(), 1)
            return True

        # Increment counter
        self.rate_limits[platform] = (last_call, calls_count + 1)
        return True

    def _make_request(self, url: str, headers: Dict = None, params: Dict = None,
                     platform: str = "unknown") -> Optional[Dict]:
        """Make HTTP request with error handling and rate limiting via sc-proxy"""
        self._check_rate_limit(platform)

        try:
            # Configure proxy if available (for routing through sc-proxy)
            proxies = None
            proxy_host = os.environ.get("PROXY_HOST")
            proxy_port = os.environ.get("PROXY_PORT")

            if proxy_host and proxy_port:
                # Handle IPv6 addresses - wrap in brackets
                if ':' in proxy_host and not proxy_host.startswith('['):
                    proxy_host = f"[{proxy_host}]"
                proxy_url = f"http://{proxy_host}:{proxy_port}"
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }

            response = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Check for specific HTTP errors
            if hasattr(e, 'response') and e.response:
                if e.response.status_code == 429:
                    print(f"Rate limited by {platform}. Try again later.", file=sys.stderr)
                elif e.response.status_code == 401:
                    print(f"Authentication failed for {platform}. Check your API credentials.", file=sys.stderr)
                else:
                    print(f"HTTP error for {platform}: {e}", file=sys.stderr)
            else:
                print(f"Request failed for {platform}: {e}", file=sys.stderr)
            return None

    # ============== Twitter/X API Methods (via TwitterAPI.io) ==============

    def get_twitter_user_info(self, username: str) -> Optional[Dict]:
        """
        Fetch detailed user profile information using TwitterAPI.io.

        Args:
            username: Twitter username (without @)

        Returns:
            Dict with user profile data
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            print("Set TWITTER_API_KEY environment variable", file=sys.stderr)
            return None

        url = "https://api.twitterapi.io/twitter/user/info"
        headers = {
            "X-API-Key": self.api_key
        }
        params = {
            "userName": username.lstrip('@')
        }

        data = self._make_request(url, headers=headers, params=params, platform="twitter")

        if not data or data.get("status") != "success":
            print(f"Failed to fetch user info: {data.get('msg', 'Unknown error')}", file=sys.stderr)
            return None

        user = data.get("data", {})

        return {
            "id": user.get("id"),
            "username": user.get("userName"),
            "name": user.get("name"),
            "description": user.get("description", ""),
            "created_at": user.get("createdAt"),
            "verified": user.get("isBlueVerified", False),
            "followers_count": user.get("followers", 0),
            "following_count": user.get("following", 0),
            "tweet_count": user.get("statusesCount", 0),
            "listed_count": user.get("listedCount", 0),
            "profile_image_url": user.get("profileImage", ""),
            "profile_banner_url": user.get("profileBanner", ""),
            "url": user.get("url", ""),
            "location": user.get("location", ""),
            "unavailable": user.get("unavailable", False)
        }

    def get_twitter_user_timeline(self, username: str, max_results: int = 100, include_replies: bool = False) -> List[Dict]:
        """
        Fetch recent tweets from a user's timeline using TwitterAPI.io.

        Args:
            username: Twitter username (without @)
            max_results: Number of tweets to fetch (fetches in batches of 20)
            include_replies: Include reply tweets

        Returns:
            List of tweet objects with full metadata
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        # First, get user info to get user ID
        user_info = self.get_twitter_user_info(username)
        if not user_info:
            return []

        user_id = user_info["id"]
        all_tweets = []
        cursor = ""

        url = "https://api.twitterapi.io/twitter/user/tweet_timeline"
        headers = {
            "X-API-Key": self.api_key
        }

        # Fetch tweets in batches (20 per page)
        while len(all_tweets) < max_results:
            params = {
                "userId": user_id,
                "includeReplies": str(include_replies).lower(),
                "includeParentTweet": "false",
                "cursor": cursor
            }

            data = self._make_request(url, headers=headers, params=params, platform="twitter")

            if not data or data.get("status") != "success":
                break

            # Tweets are in data.tweets, not root.tweets
            tweets = data.get("data", {}).get("tweets", [])
            if not tweets:
                break

            for tweet in tweets:
                all_tweets.append(self._parse_twitterapio_tweet(tweet))

            # Check if there are more pages
            if not data.get("has_next_page"):
                break

            cursor = data.get("next_cursor", "")
            if not cursor:
                break

        return all_tweets[:max_results]

    def search_twitter_tweets(self, query: str, query_type: str = "Latest", max_results: int = 100) -> List[Dict]:
        """
        Search for tweets matching a query using TwitterAPI.io.

        Args:
            query: Search query (e.g., "AI" OR "machine learning" from:username since:2024-01-01)
            query_type: "Latest" or "Top"
            max_results: Number of results to fetch

        Returns:
            List of matching tweets
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        all_tweets = []
        cursor = ""

        url = "https://api.twitterapi.io/twitter/tweet/advanced_search"
        headers = {
            "X-API-Key": self.api_key
        }

        while len(all_tweets) < max_results:
            params = {
                "query": query,
                "queryType": query_type,
                "cursor": cursor
            }

            data = self._make_request(url, headers=headers, params=params, platform="twitter")

            if not data:
                break

            # Tweets might be in data.tweets or data.data.tweets depending on endpoint
            tweets = data.get("data", {}).get("tweets", []) or data.get("tweets", [])
            if not tweets:
                break

            for tweet in tweets:
                all_tweets.append(self._parse_twitterapio_tweet(tweet))

            # Check if there are more pages
            if not data.get("has_next_page"):
                break

            cursor = data.get("next_cursor", "")
            if not cursor:
                break

        return all_tweets[:max_results]

    def get_twitter_hashtag_tweets(self, hashtag: str, max_results: int = 100) -> List[Dict]:
        """
        Search for tweets with a specific hashtag.

        Args:
            hashtag: Hashtag to search (with or without #)
            max_results: Number of results

        Returns:
            List of tweets using the hashtag
        """
        # Remove # if present
        hashtag = hashtag.lstrip('#')

        # Search for the hashtag
        query = f"#{hashtag}"
        return self.search_twitter_tweets(query, "Top", max_results)

    def get_user_followers(self, username: str, max_results: int = 200) -> List[Dict]:
        """
        Get followers of a user (200 per page, newest first).

        Args:
            username: Twitter username (without @)
            max_results: Maximum number of followers to fetch

        Returns:
            List of user objects with follower data
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        url = "https://api.twitterapi.io/twitter/user/followers"
        headers = {"X-API-Key": self.api_key}

        all_followers = []
        cursor = ""

        while len(all_followers) < max_results:
            params = {
                "userName": username.lstrip('@'),
                "cursor": cursor,
                "pageSize": min(200, max_results - len(all_followers))
            }

            data = self._make_request(url, headers=headers, params=params, platform="twitter")
            if not data or data.get("status") != "success":
                break

            followers = data.get("followers", [])
            if not followers:
                break

            for follower in followers:
                all_followers.append(self._parse_user_object(follower))

            if not data.get("has_next_page"):
                break
            cursor = data.get("next_cursor", "")
            if not cursor:
                break

        return all_followers[:max_results]

    def get_user_followings(self, username: str, max_results: int = 200) -> List[Dict]:
        """
        Get accounts that a user follows.

        Args:
            username: Twitter username (without @)
            max_results: Maximum number to fetch

        Returns:
            List of user objects
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        url = "https://api.twitterapi.io/twitter/user/followings"
        headers = {"X-API-Key": self.api_key}

        all_followings = []
        cursor = ""

        while len(all_followings) < max_results:
            params = {
                "userName": username.lstrip('@'),
                "cursor": cursor,
                "pageSize": min(200, max_results - len(all_followings))
            }

            data = self._make_request(url, headers=headers, params=params, platform="twitter")
            if not data or data.get("status") != "success":
                break

            followings = data.get("followings", [])
            if not followings:
                break

            for following in followings:
                all_followings.append(self._parse_user_object(following))

            if not data.get("has_next_page"):
                break
            cursor = data.get("next_cursor", "")
            if not cursor:
                break

        return all_followings[:max_results]

    def get_tweet_retweeters(self, tweet_id: str, max_results: int = 100) -> List[Dict]:
        """
        Get users who retweeted a tweet.

        Args:
            tweet_id: Tweet ID
            max_results: Maximum number of users to fetch

        Returns:
            List of user objects with follower counts
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        url = "https://api.twitterapi.io/twitter/tweet/retweeters"
        headers = {"X-API-Key": self.api_key}

        all_retweeters = []
        cursor = ""

        while len(all_retweeters) < max_results:
            params = {
                "tweetId": tweet_id,
                "cursor": cursor
            }

            data = self._make_request(url, headers=headers, params=params, platform="twitter")
            if not data:
                break

            users = data.get("users", [])
            if not users:
                break

            for user in users:
                all_retweeters.append(self._parse_user_object(user))

            if not data.get("has_next_page"):
                break
            cursor = data.get("next_cursor", "")
            if not cursor:
                break

        return all_retweeters[:max_results]

    def get_tweet_replies(self, tweet_id: str, max_results: int = 100) -> List[Dict]:
        """
        Get replies to a tweet.

        Args:
            tweet_id: Tweet ID
            max_results: Maximum number of replies to fetch

        Returns:
            List of tweet objects (replies) with author data including follower counts
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        url = "https://api.twitterapi.io/twitter/tweet/replies"
        headers = {"X-API-Key": self.api_key}

        all_replies = []
        cursor = ""

        while len(all_replies) < max_results:
            params = {
                "tweetId": tweet_id,
                "cursor": cursor
            }

            data = self._make_request(url, headers=headers, params=params, platform="twitter")
            if not data or data.get("status") != "success":
                break

            # API returns replies in "tweets" key, not "replies"
            replies = data.get("tweets", []) or data.get("replies", [])
            if not replies:
                break

            for reply in replies:
                all_replies.append(self._parse_twitterapio_tweet(reply))

            if not data.get("has_next_page"):
                break
            cursor = data.get("next_cursor", "")
            if not cursor:
                break

        return all_replies[:max_results]

    def get_tweet_thread_context(self, tweet_id: str, max_results: int = 100) -> List[Dict]:
        """
        Get the full thread/conversation context for a tweet.

        Args:
            tweet_id: Tweet ID (can be reply or original tweet)
            max_results: Maximum tweets in thread to fetch

        Returns:
            List of tweets in the conversation thread
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        url = "https://api.twitterapi.io/twitter/tweet/thread_context"
        headers = {"X-API-Key": self.api_key}

        all_tweets = []
        cursor = ""

        while len(all_tweets) < max_results:
            params = {
                "tweetId": tweet_id,
                "cursor": cursor
            }

            data = self._make_request(url, headers=headers, params=params, platform="twitter")
            if not data or data.get("status") != "success":
                break

            # API returns thread tweets in "tweets" key, not "replies"
            thread_tweets = data.get("tweets", []) or data.get("replies", [])
            if not thread_tweets:
                break

            for tweet in thread_tweets:
                all_tweets.append(self._parse_twitterapio_tweet(tweet))

            if not data.get("has_next_page"):
                break
            cursor = data.get("next_cursor", "")
            if not cursor:
                break

        return all_tweets[:max_results]

    def batch_get_user_by_userids(self, user_ids: List[str]) -> List[Dict]:
        """
        Batch fetch user information by user IDs (efficient for multiple users).

        Args:
            user_ids: List of Twitter user IDs

        Returns:
            List of user objects
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        url = "https://api.twitterapi.io/twitter/user/batch_info_by_ids"
        headers = {"X-API-Key": self.api_key}

        # API accepts comma-separated IDs
        params = {
            "userIds": ",".join(user_ids)
        }

        data = self._make_request(url, headers=headers, params=params, platform="twitter")
        if not data or data.get("status") != "success":
            return []

        users = data.get("users", [])
        return [self._parse_user_object(user) for user in users]

    def check_follow_relationship(self, source_username: str, target_username: str) -> bool:
        """
        Check if source_username follows target_username.

        Args:
            source_username: Username to check (does this user follow target?)
            target_username: Target username

        Returns:
            True if source follows target, False otherwise
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return False

        url = "https://api.twitterapi.io/twitter/user/follow_relationship"
        headers = {"X-API-Key": self.api_key}

        params = {
            "sourceUserName": source_username.lstrip('@'),
            "targetUserName": target_username.lstrip('@')
        }

        data = self._make_request(url, headers=headers, params=params, platform="twitter")
        if not data or data.get("status") != "success":
            return False

        return data.get("data", {}).get("following", False)

    def get_user_verified_followers(self, user_id: str, max_results: int = 100) -> List[Dict]:
        """
        Get verified followers of a user (costs $0.3 per 1,000).

        Args:
            user_id: Twitter user ID (not username)
            max_results: Maximum verified followers to fetch

        Returns:
            List of verified follower user objects
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        url = "https://api.twitterapi.io/twitter/user/verifiedFollowers"
        headers = {"X-API-Key": self.api_key}

        all_followers = []
        cursor = ""

        while len(all_followers) < max_results:
            params = {
                "user_id": user_id,
                "cursor": cursor
            }

            data = self._make_request(url, headers=headers, params=params, platform="twitter")
            if not data or data.get("status") != "success":
                break

            followers = data.get("followers", [])
            if not followers:
                break

            for follower in followers:
                all_followers.append(self._parse_user_object(follower))

            if not data.get("has_next_page"):
                break
            cursor = data.get("next_cursor", "")
            if not cursor:
                break

        return all_followers[:max_results]

    def get_trends(self, woeid: int = 1) -> List[Dict]:
        """
        Get trending topics by location (default: worldwide).

        Args:
            woeid: Where On Earth ID (1=worldwide, 2418046=Washington DC, etc.)
                   Full list: https://gist.github.com/tedyblood/5bb5a9f78314cc1f478b3dd7cde790b9

        Returns:
            List of trending topics with rank and meta description
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return []

        url = "https://api.twitterapi.io/twitter/trends"
        headers = {"X-API-Key": self.api_key}

        params = {
            "woeid": woeid,
            "num": 30  # Default to 30 trends
        }

        data = self._make_request(url, headers=headers, params=params, platform="twitter")
        if not data or data.get("status") != "success":
            return []

        trends = data.get("trends", [])
        return [{
            "name": trend.get("name"),
            "query": trend.get("target", {}).get("query"),
            "rank": trend.get("rank"),
            "meta_description": trend.get("meta_description", "")
        } for trend in trends]

    def get_space_detail(self, space_id: str) -> Optional[Dict]:
        """
        Get details about a Twitter Space (live audio event).

        Args:
            space_id: Twitter Space ID

        Returns:
            Dict with Space information (metadata, participants, stats)
        """
        if not self.api_key:
            print("TwitterAPI.io API key not configured", file=sys.stderr)
            return None

        url = "https://api.twitterapi.io/twitter/spaces/detail"
        headers = {"X-API-Key": self.api_key}

        params = {"space_id": space_id}

        data = self._make_request(url, headers=headers, params=params, platform="twitter")
        if not data or data.get("status") != "success":
            return None

        space_data = data.get("data", {})
        return {
            "id": space_data.get("id"),
            "title": space_data.get("title"),
            "state": space_data.get("state"),  # NotStarted/Live/Ended
            "created_at": space_data.get("created_at"),
            "scheduled_start": space_data.get("scheduled_start"),
            "live_listener_count": space_data.get("live_listener_count", 0),
            "total_replay_watched": space_data.get("total_replay_watched", 0),
            "creator": space_data.get("creator", {}),
            "participants": space_data.get("participants", {})
        }

    def _parse_user_object(self, user: Dict) -> Dict:
        """Parse TwitterAPI.io user object into standardized format"""
        return {
            "id": user.get("id"),
            "username": user.get("userName"),
            "name": user.get("name"),
            "description": user.get("description", ""),
            "created_at": user.get("createdAt"),
            "verified": user.get("isBlueVerified", False),
            "verified_type": user.get("verifiedType"),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "tweet_count": user.get("statusesCount", 0),
            "media_count": user.get("mediaCount", 0),
            "favourites_count": user.get("favouritesCount", 0),
            "profile_image_url": user.get("profilePicture", ""),
            "profile_banner_url": user.get("coverPicture", ""),
            "location": user.get("location", ""),
            "url": user.get("url", ""),
            "can_dm": user.get("canDm", False),
            "unavailable": user.get("unavailable", False)
        }

    def _parse_twitterapio_tweet(self, tweet: Dict) -> Dict:
        """Parse TwitterAPI.io tweet object into standardized format"""
        # Extract author info
        author = tweet.get("author", {})

        # Detect tweet type
        is_reply = tweet.get("inReplyToStatusId") is not None
        is_retweet = tweet.get("type") == "retweet"
        is_quote = tweet.get("quotedTweet") is not None

        # Extract entities
        entities = tweet.get("entities", {})
        hashtags = [tag.get("text", "") for tag in entities.get("hashtags", [])]
        mentions = [mention.get("screenName", "") for mention in entities.get("userMentions", [])]
        urls = [url.get("expandedUrl", "") for url in entities.get("urls", [])]

        return {
            "id": tweet.get("id"),
            "conversation_id": tweet.get("conversationId"),
            "text": tweet.get("text", ""),
            "created_at": tweet.get("createdAt"),
            "likes": tweet.get("likeCount", 0),
            "retweets": tweet.get("retweetCount", 0),
            "replies": tweet.get("replyCount", 0),
            "quotes": tweet.get("quoteCount", 0),
            "views": tweet.get("viewCount", 0),
            "bookmarks": tweet.get("bookmarkCount", 0),
            "is_reply": is_reply,
            "is_retweet": is_retweet,
            "is_quote": is_quote,
            "hashtags": hashtags,
            "mentions": mentions,
            "urls": urls,
            "url": tweet.get("url", f"https://twitter.com/i/web/status/{tweet.get('id')}"),
            "author": {
                "id": author.get("id"),
                "username": author.get("userName"),
                "name": author.get("name"),
                "followers": author.get("followers", 0),
                "verified": author.get("isBlueVerified", False)
            }
        }


def main():
    """Test the Twitter API client"""
    client = APIClient()

    print("Testing Twitter API Client...")
    print("\nNote: Requires TWITTER_API_KEY environment variable")

    if client.api_key:
        print("\nFetching info for @elonmusk...")
        user_info = client.get_twitter_user_info("elonmusk")
        if user_info:
            print(f"  Name: {user_info['name']}")
            print(f"  Followers: {user_info['followers_count']:,}")
            print(f"  Tweets: {user_info['tweet_count']:,}")
    else:
        print("Twitter API key not configured. Set TWITTER_API_KEY environment variable")

    print("\nAPI client test complete.")


if __name__ == "__main__":
    main()
