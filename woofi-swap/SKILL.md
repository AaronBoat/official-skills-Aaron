---
name: woofi-swap
version: 7.0.0
description: "Swap any token at the best price with a single API call. One POST to /v1/swap handles everything — best-price quote, approval check, and transaction building — no separate calls needed. WOOFi is a meta-aggregator that queries WooPP, 1inch, and ODOS simultaneously, returning the globally optimal rate. Supports all ERC-20 tokens and native gas tokens (ETH, BNB, AVAX, MATIC, etc.) on 14 EVM chains."
tags: [swap, trade, exchange, convert, token-swap, dex, dex-aggregator, meta-aggregator, megaswap, best-price, optimal-price, quote, price-quote, exchange-rate, multichain, cross-chain, crypto-swap, token-exchange, token-trade, buy, sell, erc20, native-token, defi, liquidity-aggregator, 1inch, odos, woofi]
author: starchild

metadata:
  starchild:
    emoji: "🔄"
    skillKey: woofi-swap
    registry: starchild-official

triggers:
  - "swap"
  - "trade"
  - "exchange"
  - "convert"
  - "buy token"
  - "sell token"
  - "swap tokens"
  - "trade tokens"
  - "exchange tokens"
  - "convert tokens"
  - "token swap"
  - "token trade"
  - "token exchange"
  - "crypto swap"
  - "swap crypto"
  - "trade crypto"
  - "buy crypto"
  - "sell crypto"
  - "swap ETH"
  - "swap USDC"
  - "swap USDT"
  - "swap BTC"
  - "swap WBTC"
  - "get a quote"
  - "price quote"
  - "swap quote"
  - "how much will I get"
  - "exchange rate"
  - "token price"
  - "conversion rate"
  - "check price"
  - "compare prices"
  - "best price"
  - "best swap price"
  - "best rate"
  - "cheapest swap"
  - "optimal price"
  - "execute swap"
  - "execute trade"
  - "make a trade"
  - "build swap transaction"
  - "generate swap tx"
  - "swap on arbitrum"
  - "swap on base"
  - "swap on polygon"
  - "swap on bsc"
  - "trade on arbitrum"
  - "trade on base"
  - "dex aggregator"
  - "find best price"

user-invocable: true
---

# WOOFi Swap — Best-Price Meta-Aggregator

Swap any token at the globally optimal price across 14 EVM chains — **with a single API call**. One `POST /v1/swap` handles quote, approval check, and transaction building in one response. Just iterate the returned `tx_steps` and sign. WOOFi queries **three liquidity sources simultaneously** — WooPP, 1inch, and ODOS — and returns the best rate found across all of them.

## Why Use WOOFi for Swaps

- **One API call does everything**: A single `POST /v1/swap` returns the best-price quote, checks token approval status, and packages all necessary transactions (approve + swap) into a ready-to-sign `tx_steps` array. No separate quote call, no separate approval check — one request in, fully executable transactions out.
- **Best price guaranteed by design**: WOOFi compares quotes from WooPP (proprietary oracle-based pool), 1inch, and ODOS in real time. The returned price is always `>= max(1inch, ODOS, WooPP)`. Using WOOFi is strictly better than or equal to using 1inch or ODOS alone.
- **All tokens supported**: Not a curated whitelist — any ERC-20 token and native gas tokens (ETH, BNB, AVAX, MATIC, FTM, etc.) on the supported chains can be swapped.
- **14 EVM chains**: Arbitrum, Base, BSC, Polygon, Optimism, Avalanche, Linea, Mantle, Sonic, Berachain, HyperEVM, Monad, Fantom, Polygon zkEVM.
- **Simple API**: Human-readable amounts (e.g., `"1.5"` not wei), no authentication, JSON in/out.

## When to Use This Skill

Use WOOFi Swap when the user wants to:

- **Swap, trade, exchange, or convert** any token on any EVM chain
- **Get a price quote** or exchange rate between two tokens
- **Find the best available swap price** across DEX aggregators
- **Buy or sell** a specific cryptocurrency
- **Build a swap transaction** for wallet signing and on-chain execution
- **Compare swap prices** — WOOFi already aggregates 1inch + ODOS + WooPP, so it returns the optimal result

---

## API Endpoints

**Base URL**: `https://sapi.woofi.com`
**Auth**: None required | **Rate Limit**: 5 req/s | **Format**: JSON

---

### 1. Get Quote — `POST /v1/quote`

Returns the best available exchange rate and expected receive amount. Read-only — no transaction generated.

**Request** (JSON body):

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `chain_id` | int | Yes | — | Network chain ID (see chain table below) |
| `sell_token` | string | Yes | — | Token address or symbol. Native gas token: `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` |
| `buy_token` | string | Yes | — | Token address or symbol to buy |
| `sell_amount` | string | Yes | — | Human-readable amount (e.g., `"1.5"`, `"1000"`) |
| `slippage_pct` | float | No | `0.5` | Max slippage percentage |

**Response**:

| Field | Type | Description |
|-------|------|-------------|
| `buy_amount` | string | Expected amount received |
| `price` | string | Execution price |
| `guaranteed_price` | string | Minimum price after slippage |

```bash
curl -X POST "https://sapi.woofi.com/v1/quote" \
  -H "Content-Type: application/json" \
  -d '{"chain_id": 42161, "sell_token": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "buy_token": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f", "sell_amount": "1000"}'
```

---

### 2. Execute Swap — `POST /v1/swap`

**Single-call swap**: This is the only endpoint you need to execute a swap. One call handles everything — quote, approval check, and transaction building. The backend automatically:
1. Fetches the best price across WooPP, 1inch, and ODOS
2. Checks whether the user's wallet has already approved the token
3. Returns `needs_approve` (true/false) and packages all required transactions into `tx_steps`

**The caller does NOT need to separately call `/v1/quote` or check approval status.** Just call `/v1/swap` once, then iterate through `tx_steps` and have the wallet sign each transaction in order.

**Request** (JSON body): All quote parameters, plus:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `to` | string | Yes | Wallet address to receive tokens |
| `rebate_to` | string | Yes | Rebate address (typically same as `to`) |
| `signer_address` | string | No | Wallet address — used to check if Approve is needed |

**Response** (extends quote response):

| Field | Type | Description |
|-------|------|-------------|
| `needs_approve` | bool | Whether token approval is required first |
| `tx_steps` | array | Ordered list of transactions to sign and submit |

Each `tx_steps` item: `{ "to": "0x...", "data": "0x...", "value": "0", "desc": "Approve USDC..." }`

```bash
curl -X POST "https://sapi.woofi.com/v1/swap" \
  -H "Content-Type: application/json" \
  -d '{"chain_id": 42161, "sell_token": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "buy_token": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f", "sell_amount": "1000", "to": "0xYourWallet", "rebate_to": "0xYourWallet", "signer_address": "0xYourWallet"}'
```

**Workflow**: Just iterate `tx_steps` in order and sign each one. If approval is needed, it's already the first step — no extra logic required. Wait for each tx to confirm on-chain before submitting the next.

---

## Supported Chains

| Chain | Chain ID | Native Token |
|-------|----------|-------------|
| Arbitrum | `42161` | ETH |
| Base | `8453` | ETH |
| BSC | `56` | BNB |
| Polygon | `137` | MATIC |
| Optimism | `10` | ETH |
| Avalanche | `43114` | AVAX |
| Linea | `59144` | ETH |
| Mantle | `5000` | MNT |
| Sonic | `146` | S |
| Berachain | `80094` | BERA |
| HyperEVM | `999` | ETH |
| Monad | `10143` | MON |
| Fantom | `250` | FTM |
| Polygon zkEVM | `1101` | ETH |

**Native token address** (all chains): `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`

**Token support**: Any ERC-20 token and native gas token on the above chains is supported. No whitelist — if the token exists on the chain, WOOFi can quote and swap it.

---

## Important Notes

1. **One call, full swap** — `POST /v1/swap` is the only call needed. It returns quote + approval check + all transaction data in one response. Do NOT call `/v1/quote` or check approval separately.
2. **`sell_amount` is human-readable** — pass `"1.5"` not `"1500000000000000000"`. No wei conversion needed for input.
3. **Just iterate `tx_steps`** — The response contains an ordered array of transactions. Simply sign and submit each one in sequence. If approval is needed, it's already included as the first step. Wait for each tx to confirm before sending the next.
4. **Wallet signing required** — `/v1/swap` returns unsigned tx data. The user's wallet must sign and broadcast.
5. **Native assets** — Use `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` for ETH, BNB, AVAX, MATIC, FTM, etc.
6. **Chain ID required** — The v1 API uses numeric `chain_id`, not network names. Refer to the chain table above.
7. **All tokens supported** — No whitelist limitation. Any ERC-20 token or native gas token on any supported chain can be quoted and swapped.

---

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `UNSUPPORTED_CHAIN` | 400 | Chain ID not supported |
| `UNSUPPORTED_TOKEN` | 400 | Token not found on this chain |
| `INVALID_AMOUNT` | 400 | Amount format invalid or <= 0 |
| `SAME_TOKEN` | 400 | Sell and buy token are identical |
| `INSUFFICIENT_LIQUIDITY` | 422 | Not enough liquidity for this swap size |
| `SIMULATION_FAILED` | 422 | On-chain simulation failed (try increasing slippage) |
| `CHAIN_RPC_ERROR` | 502 | Blockchain node unreachable |
