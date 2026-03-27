"""
Jupiter operations — quote and build swap transactions on Solana.
Usage: python scripts/jupiter_ops.py <action> [args]
Actions:
  quote <input_mint> <output_mint> <amount_lamports> [slippage_bps] — Get swap quote
  swap <input_mint> <output_mint> <amount_lamports> <user_pubkey> [slippage_bps] — Build swap tx (base64)
  tokens [query]                                                    — Search token mints
"""
import sys
import json
import requests

BASE = "https://lite-api.jup.ag"

KNOWN_TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
}

DECIMALS = {
    "So11111111111111111111111111111111111111112": 9,
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6,
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": 6,
}


def resolve_mint(token: str) -> str:
    """Resolve symbol or address to mint address."""
    upper = token.upper()
    if upper in KNOWN_TOKENS:
        return KNOWN_TOKENS[upper]
    return token  # assume it's already a mint address


def format_amount(raw: str, mint: str) -> str:
    decimals = DECIMALS.get(mint, 9)
    val = int(raw) / (10 ** decimals)
    return f"{val:,.6f}".rstrip('0').rstrip('.')


def get_quote(input_mint: str, output_mint: str, amount: str, slippage_bps: int = 50):
    url = f"{BASE}/swap/v1/quote"
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "slippageBps": slippage_bps,
        "restrictIntermediateTokens": "true",
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    quote = resp.json()
    in_amt = format_amount(quote.get("inAmount", amount), input_mint)
    out_amt = format_amount(quote.get("outAmount", "0"), output_mint)
    impact = quote.get("priceImpactPct", "N/A")
    routes = quote.get("routePlan", [])
    print("Quote:")
    print(f"  In:  {in_amt} ({input_mint[:8]}...)")
    print(f"  Out: {out_amt} ({output_mint[:8]}...)")
    print(f"  Price Impact: {impact}%")
    print(f"  Route Steps: {len(routes)}")
    for i, r in enumerate(routes):
        swap_info = r.get("swapInfo", {})
        label = swap_info.get("label", "Unknown")
        pct = r.get("percent", 100)
        print(f"    Step {i+1}: {label} ({pct}%)")
    print()
    return quote


def build_swap(input_mint: str, output_mint: str, amount: str, user_pubkey: str, slippage_bps: int = 50):
    # Step 1: get quote
    quote = get_quote(input_mint, output_mint, amount, slippage_bps)
    # Step 2: build swap tx
    url = f"{BASE}/swap/v1/swap"
    payload = {
        "quoteResponse": quote,
        "userPublicKey": user_pubkey,
        "dynamicComputeUnitLimit": True,
        "dynamicSlippage": True,
        "prioritizationFeeLamports": {
            "priorityLevelWithMaxLamports": {
                "maxLamports": 1000000,
                "priorityLevel": "medium",
            }
        },
    }
    resp = requests.post(url, json=payload, timeout=20)
    resp.raise_for_status()
    result = resp.json()
    swap_tx = result.get("swapTransaction", "")
    if swap_tx:
        print("Swap Transaction (base64):")
        print(f"  {swap_tx[:80]}...")
        print(f"  Length: {len(swap_tx)} chars")
        print()
        print("To execute, call:")
        print(f'  wallet_sol_transfer(transaction="{swap_tx[:40]}...")')
    else:
        print("Error: No swap transaction returned")
        print(json.dumps(result, indent=2))
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    if action == "quote":
        if len(sys.argv) < 5:
            print("Usage: quote <input_mint_or_symbol> <output_mint_or_symbol> <amount_lamports> [slippage_bps]")
            sys.exit(1)
        in_mint = resolve_mint(sys.argv[2])
        out_mint = resolve_mint(sys.argv[3])
        amount = sys.argv[4]
        slippage = int(sys.argv[5]) if len(sys.argv) > 5 else 50
        get_quote(in_mint, out_mint, amount, slippage)
    elif action == "swap":
        if len(sys.argv) < 6:
            print(
                "Usage: swap <input_mint> <output_mint>"
                " <amount_lamports> <user_pubkey> [slippage_bps]")
            sys.exit(1)
        in_mint = resolve_mint(sys.argv[2])
        out_mint = resolve_mint(sys.argv[3])
        amount = sys.argv[4]
        pubkey = sys.argv[5]
        slippage = int(sys.argv[6]) if len(sys.argv) > 6 else 50
        build_swap(in_mint, out_mint, amount, pubkey, slippage)
    elif action == "tokens":
        query = sys.argv[2] if len(sys.argv) > 2 else None
        print("Known tokens:")
        for sym, addr in KNOWN_TOKENS.items():
            if query is None or query.upper() in sym:
                print(f"  {sym}: {addr}")
    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
