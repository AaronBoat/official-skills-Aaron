---
name: twitter
version: 1.3.0
description: Twitter/X (x.com) data lookup — fetch tweets by URL or ID, search tweets, user profiles, followers, replies. Use for ANY x.com or twitter.com URL.
tools:
  - twitter_search_tweets
  - twitter_get_tweets
  - twitter_user_info
  - twitter_user_tweets
  - twitter_user_followers
  - twitter_user_followings
  - twitter_tweet_replies
  - twitter_tweet_retweeters
  - twitter_search_users

metadata:
  starchild:
    emoji: "🐦"
    skillKey: twitter
    requires:
      env: [TWITTER_API_KEY]

user-invocable: false
disable-model-invocation: false
---

# Twitter / X Data

Read-only access to Twitter/X via twitterapi.io. Use these tools to look up tweets, users, followers, and social activity.

## 🔴 HARD LIMITS — READ FIRST

> **⛔ CALL AT MOST 3 TWITTER TOOLS PER RESPONSE. STOP AFTER 3 CALLS.**
> After each tool call, check: "Do I have enough data to answer?" If yes → STOP AND REPLY.
> **⛔ NEVER call `bash` or `write_file` for any twitter task** — reason inline, no scripts.
> **⛔ NEVER paginate unless user explicitly asks for more** — first page is enough.
> **⛔ NEVER call `lunar_coin`, `lunar_coin_time_series`, or any LunarCrush/CoinGecko tool** — Twitter sentiment 问题只用 `twitter_search_tweets` 回答，不跨 skill。
> **⛔ NEVER call `coin_price`, `cg_trending`, `cg_coins_markets`** — 价格数据超出 Twitter skill 范围。

## 🔗 URL Handling — x.com / twitter.com

> **⛔ NEVER use `web_fetch` for x.com or twitter.com URLs** — Twitter blocks scraping, you'll only get a login wall.
> **✅ ALWAYS extract the tweet ID from the URL and use `twitter_get_tweets`.**

| URL pattern | Extract | Tool call |
|-------------|---------|-----------|
| `x.com/{user}/status/{id}` | tweet ID = `{id}` | `twitter_get_tweets(tweet_ids=["{id}"])` |
| `twitter.com/{user}/status/{id}` | tweet ID = `{id}` | `twitter_get_tweets(tweet_ids=["{id}"])` |
| `x.com/{user}` | username = `{user}` | `twitter_user_info(username="{user}")` |

**Example:** User sends `https://x.com/zerohedge/status/2042670029548794219`
→ Extract ID: `2042670029548794219`
→ Call: `twitter_get_tweets(tweet_ids=["2042670029548794219"])`
→ Never: `web_fetch("https://x.com/...")`

## 💡 Few-Shot Examples

**Q: 找 3 个关于 BTC ETF 的高赞推文，只要 ID 和点赞数**
→ PLAN: 1 call `twitter_search_tweets("BTC ETF min_faves:100")` → pick top 3 from results → reply JSON
→ STOP after 1 call. Total tools: 1

**Q: @elonmusk 最近发的推文哪条点赞最多？只要数字**
→ PLAN: 1 call `twitter_user_tweets("elonmusk")` → find max likes in results → reply number
→ STOP after 1 call. Total tools: 1

**Q: 搜索 solana 推文，找点赞最多那条的作者**
→ PLAN: 1 call `twitter_search_tweets("solana")` → find tweet with most likes → extract username
→ STOP after 1 call. Total tools: 1

**Q: 对比 @A 和 @B 谁粉丝多，再看粉丝多的最新推文**
→ PLAN: call `twitter_user_info("A")` + `twitter_user_info("B")` → determine winner → call `twitter_user_tweets(winner)`
→ Total tools: 3. STOP.

## ⚡ FAST PATHS (act immediately, no clarification needed)

| Trigger keywords | Action |
|-----------------|--------|
| x.com or twitter.com URL with `/status/{id}` | Extract tweet ID → `twitter_get_tweets(tweet_ids=["{id}"])` — **never web_fetch** |
| x.com or twitter.com URL with `/{username}` only | Extract username → `twitter_user_info(username="{username}")` |
| crypto sentiment / 情绪扫描 / market mood / BTC ETH SOL 讨论 | Call `twitter_search_tweets` once per coin: `"$BTC"`, `"$ETH"`, `"$SOL"` — summarize tone, **no user profile lookups** |
| search tweets about X | Call `twitter_search_tweets` with the topic |
| who is @username | Call `twitter_user_info` |
| what did @username post | Call `twitter_user_tweets` |

## Tool Decision Tree

**"Search for tweets about a topic"** → `twitter_search_tweets`
Advanced query with operators: keywords, from:user, #hashtag, $cashtag, min_faves, date ranges.

**"Look up a specific tweet or set of tweets"** → `twitter_get_tweets`
Pass one or more tweet IDs directly.

**"Who is this Twitter account?"** → `twitter_user_info`
Profile data: bio, follower count, tweet count, verification.

**"What has this account been posting?"** → `twitter_user_tweets`
Recent tweets from a specific user.

**"Who follows this account?"** → `twitter_user_followers`
List of followers for a user.

**"Who does this account follow?"** → `twitter_user_followings`
List of accounts a user follows.

**"What are people saying in reply to this tweet?"** → `twitter_tweet_replies`
Replies to a specific tweet by ID.

**"Who retweeted this?"** → `twitter_tweet_retweeters`
Users who retweeted a specific tweet.

**"Find accounts related to a topic"** → `twitter_search_users`
Search users by name or keyword.

**"Crypto sentiment scan / 情绪扫描 / market mood"** → `twitter_search_tweets` (call once per coin)
For BTC/ETH/SOL sentiment: search `"$BTC"`, `"$ETH"`, `"$SOL"` separately, then summarize tone inline.
⛔ NEVER call `twitter_user_info`, `twitter_user_followers`, or `twitter_user_tweets` during a sentiment scan — text analysis only.

## Available Tools

| Tool | Description | Key Params |
|------|-------------|------------|
| `twitter_search_tweets` | Advanced tweet search | `query` (required), `cursor` |
| `twitter_get_tweets` | Get tweets by ID | `tweet_ids` (array, required) |
| `twitter_user_info` | User profile lookup | `username` (required) |
| `twitter_user_tweets` | User's recent tweets | `username` (required), `cursor` |
| `twitter_user_followers` | User's followers | `username` (required), `cursor` |
| `twitter_user_followings` | User's followings | `username` (required), `cursor` |
| `twitter_tweet_replies` | Replies to a tweet | `tweet_id` (required), `cursor` |
| `twitter_tweet_retweeters` | Who retweeted | `tweet_id` (required), `cursor` |
| `twitter_search_users` | Search for users | `query` (required), `cursor` |

## Usage Patterns

### ⚠️ Token Budget Rules
- Sentiment scan: max **3 `twitter_search_tweets` calls** (one per coin), then summarize. Stop.
- Account research: max **2 tool calls total** unless user asks for more depth.
- Never chain more than 5 Twitter tool calls in one response.

### Research an account
1. `twitter_user_info` — get profile, follower count, bio
2. `twitter_user_tweets` — see what they've been posting
3. `twitter_user_followings` — who they follow (reveals interests)

### Track a topic or token
1. `twitter_search_tweets` with query like `"$SOL min_faves:50"` — find popular tweets
2. `twitter_search_users` with the topic — find relevant accounts

## Output Constraints (IMPORTANT for small models)

- **Max 1 `twitter_search_tweets` call per coin/topic** — do not repeat searches for same query. First result set is sufficient.
- **Max 3 `twitter_user_info` calls per response** — only look up the most relevant accounts.
- **Never call `bash` or `write_file` for Twitter data** — reason inline directly from tool results.
- **Sentiment summaries**: after 1 search call, summarize tone inline in 3–5 sentences. Done.
- **Pagination**: only fetch next page if user explicitly asks for more results.
- **After getting search results: sort/filter in your head, do not call bash to sort.**

### Analyze engagement on a tweet
1. `twitter_get_tweets` — get the tweet and its metrics
2. `twitter_tweet_replies` — see the conversation
3. `twitter_tweet_retweeters` — see who amplified it

### Find influencers in a space
1. `twitter_search_users` with keyword (e.g. "DeFi analyst")
2. `twitter_user_info` on top results to compare follower counts
3. `twitter_user_tweets` to check content quality

## Search Query Operators

The `twitter_search_tweets` tool supports advanced operators:

| Operator | Example | Description |
|----------|---------|-------------|
| keyword | `bitcoin` | Tweets containing the word |
| exact phrase | `"ethereum merge"` | Exact phrase match |
| `from:` | `from:elonmusk` | Tweets by a specific user |
| `to:` | `to:elonmusk` | Tweets replying to a user |
| `#hashtag` | `#crypto` | Tweets with hashtag |
| `$cashtag` | `$BTC` | Tweets with cashtag |
| `lang:` | `lang:en` | Filter by language |
| `has:media` | `has:media` | Tweets with images/video |
| `has:links` | `has:links` | Tweets with URLs |
| `is:reply` | `is:reply` | Only replies |
| `min_faves:` | `min_faves:100` | Minimum likes |
| `min_retweets:` | `min_retweets:50` | Minimum retweets |
| `since:` | `since:2024-01-01` | Tweets after date |
| `until:` | `until:2024-12-31` | Tweets before date |

Combine operators: `from:VitalikButerin $ETH min_faves:100 since:2024-01-01`

## Pagination

Most endpoints support cursor-based pagination. When a response includes a cursor value, pass it as the `cursor` parameter to get the next page. If no cursor is returned, you've reached the end.

## Notes

- **API key required**: Set `TWITTER_API_KEY` environment variable. Tools will error without it.
- **Read-only**: These tools only retrieve data. No posting, liking, or following.
- **Usernames**: Always pass without the `@` prefix (e.g. `"elonmusk"` not `"@elonmusk"`).
- **Tweet IDs**: Use string format for tweet IDs to avoid integer overflow issues.
- **Rate limits**: The API has rate limits. If you get rate-limited, wait before retrying.
