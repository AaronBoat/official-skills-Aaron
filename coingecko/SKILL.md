---
name: coingecko
version: 1.0.0
description: CoinGecko crypto price data, charts, market discovery, and global stats
tools:
  - coin_price
  - coin_ohlc
  - coin_chart
  - cg_trending
  - cg_top_gainers_losers
  - cg_new_coins
  - cg_global
  - cg_global_defi
  - cg_categories
  - cg_derivatives
  - cg_derivatives_exchanges
  - cg_coins_list
  - cg_coins_markets
  - cg_coin_data
  - cg_coin_tickers
  - cg_exchanges
  - cg_exchange
  - cg_exchange_tickers
  - cg_exchange_volume_chart
  - cg_nfts_list
  - cg_nft
  - cg_nft_by_contract
  - cg_asset_platforms
  - cg_exchange_rates
  - cg_vs_currencies
  - cg_categories_list
  - cg_search
  - cg_token_price
  - cg_coin_by_contract

metadata:
  starchild:
    emoji: "🦎"
    skillKey: coingecko
    requires:
      env:
        - COINGECKO_API_KEY

user-invocable: false
disable-model-invocation: false
---

# CoinGecko

CoinGecko provides comprehensive crypto market data including spot prices, OHLC candles, market cap, trending coins, sector performance, and global stats.

## When to Use CoinGecko

Use CoinGecko for:
- **Price queries** - Current prices, historical prices, OHLC data
- **Market overview** - Market cap, volume, trending coins, top gainers/losers
- **Coin information** - Detailed coin data, tickers, trading pairs
- **Exchange data** - Exchange listings, volumes, trading pairs
- **NFT data** - NFT collections, floor prices, market stats
- **Global metrics** - Total market cap, dominance, DeFi stats
- **Categories** - Sector performance (DeFi, Gaming, Layer 1, etc.)

## Tool Selection Guide (READ THIS FIRST)

**Before choosing a tool, match the user's intent:**

| User asks about... | Use this tool | NOT this |
|---------------------|---------------|----------|
| Sector/category comparison (L1 vs DeFi, Meme performance) | `cg_categories()` | ❌ `cg_coins_markets` (individual coins, not sectors) |
| NFT collection ranking, floor prices, NFT market overview | `cg_nfts_list()` | ❌ `cg_coins_markets` (tokens only, no NFT data) |
| Specific NFT collection details (BAYC, CryptoPunks) | `cg_nft(nft_id=...)` | ❌ `cg_nft_by_contract` (only if you have contract address) |
| Current coin price | `coin_price()` | ❌ `cg_coins_market_data` (that's coinglass, different skill) |
| OHLC candle data | `coin_ohlc()` | ❌ `cg_ohlc_history` (that's coinglass, different skill) |
| Exchange trading pairs | `cg_exchange_tickers()` | ❌ `cg_supported_exchanges` (that's coinglass) |

## Common Workflows

### Get Coin Price
```
coin_price(coin_id="bitcoin")  # Supports symbols like BTC, ETH, SOL
coin_price(coin_id="ethereum", vs_currencies="usd,eur")
```

### Historical Data
```
coin_ohlc(coin_id="bitcoin", vs_currency="usd", days=7)  # OHLC candles
coin_chart(coin_id="ethereum", vs_currency="usd", days=30)  # Price chart data
```

### Market Discovery
```
cg_trending()  # Trending coins in the last 24h
cg_top_gainers_losers()  # Top movers
cg_new_coins()  # Recently listed coins
cg_coins_markets(vs_currency="usd", order="market_cap_desc", per_page=100)
```

### Coin Information
```
cg_coin_data(id="bitcoin")  # Detailed coin data
cg_coin_tickers(id="ethereum")  # All trading pairs
cg_search(query="solana")  # Search for coins
```

### Exchange Data
```
cg_exchanges()  # All exchanges
cg_exchange(id="binance")  # Specific exchange
cg_exchange_tickers(id="binance")  # Exchange trading pairs
cg_exchange_volume_chart(id="binance", days=7)
```

### Global Metrics
```
cg_global()  # Total market stats
cg_global_defi()  # DeFi specific stats
```

### Sector / Category Comparison
**Use `cg_categories()` for ANY question about sector performance, category comparison, or "which sector is doing better".**
This returns ALL categories (Layer 1, DeFi, Meme, Gaming, etc.) with market cap, 24h change, and top coins — in ONE call.
Do NOT manually query individual coins with `cg_coins_markets` for category comparison — use `cg_categories()` instead.

⚡ **Efficiency: ONE call is enough.** `cg_categories()` returns all sectors at once. Do NOT call it multiple times or loop through categories individually.
```
cg_categories()  # Returns ALL sectors — L1, DeFi, Meme, etc. in one response
cg_categories(order="market_cap_change_24h_desc")  # Sort by 24h performance
```

### NFT Data
**Use `cg_nfts_list()` for NFT rankings, top NFT collections, or NFT market overview.**
**Use `cg_nft(nft_id="...")` ONLY for deep-dive on a single collection** (description, social links, historical data).
Do NOT use `cg_coins_markets` for NFT data — it only returns fungible tokens, not NFT collections.

⚡ **Efficiency: `cg_nfts_list()` already includes floor_price, market_cap, and h24_volume for each collection.** For ranking/comparison questions, one call is enough — do NOT call `cg_nft()` or `cg_nft_by_contract()` for each collection individually.
```
cg_nfts_list()  # Top NFTs with floor price + volume — one call covers ranking questions
cg_nfts_list(order="h24_volume_usd_desc")  # Sort by 24h volume
cg_nft(nft_id="bored-ape-yacht-club")  # Deep-dive only: full details for one collection
```

### Contract Address Queries
```
cg_token_price(contract_addresses=["0x..."], vs_currencies="usd")
cg_coin_by_contract(contract_address="0x...", platform="ethereum")
```

## Important Notes

- **Coin IDs**: CoinGecko uses slug IDs (e.g., "bitcoin", "ethereum", "solana"). The tools auto-resolve common symbols like BTC, ETH, SOL.
- **API Key**: Requires COINGECKO_API_KEY environment variable (Pro API)
- **Rate Limits**: Be mindful of API rate limits. Use batch endpoints when querying multiple coins.
- **vs_currencies**: Most endpoints support multiple currencies (usd, eur, btc, eth, etc.). Use `cg_vs_currencies()` to see all supported currencies.

## Symbol Resolution

Common symbols are automatically resolved:
- BTC → bitcoin
- ETH → ethereum
- SOL → solana
- USDT → tether
- USDC → usd-coin
- BNB → binancecoin

**Important:** If unsure about a coin ID, always use `cg_search(query="coin name")` first to find the exact CoinGecko ID before calling price tools.
