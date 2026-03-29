#!/usr/bin/env python3
"""
Coinglass Funding Rate Module

Fetch funding rates across major cryptocurrency exchanges including
Binance, OKX, Bybit, KuCoin, MEXC, Bitfinex, Kraken, and more.
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional, List

from ._api import cg_request

# Supported exchanges
EXCHANGES = [
    "Binance", "OKX", "Bybit", "KuCoin", "MEXC", "CoinEx",
    "Bitfinex", "Kraken", "dYdX", "Gate", "Bitmex"
]

SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "XRP",
    "DOGE", "ADA", "AVAX", "LINK", "MATIC"
]


def get_funding_rates(
    symbol: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch funding rates across all exchanges.

    Args:
        symbol: Optional symbol filter (BTC, ETH, etc.).

    Returns:
        Dict with funding rate data. If symbol given, filtered to
        that symbol only.

    Raises:
        CoinglassError: On API failure.
    """
    data = cg_request("funding", version="v2")

    if symbol and isinstance(data, list):
        filtered = [
            d for d in data
            if d.get("symbol", "").upper() == symbol.upper()
        ]
        return filtered

    return data


def get_symbol_funding_rate(
    symbol: str,
    exchange: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get funding rate for a specific symbol and optionally a specific
    exchange.

    Args:
        symbol: Symbol to query (BTC, ETH, etc.)
        exchange: Optional exchange name (Binance, OKX, etc.)

    Returns:
        Dict with rate, rate_percent, next_funding_time, etc.
        None if no data found for the given symbol/exchange.
    """
    data = get_funding_rates(symbol)
    if not data:
        return None

    symbol_data = data[0] if isinstance(data, list) and data else None
    if not symbol_data:
        return None

    if exchange:
        for rate_info in symbol_data.get("uMarginList", []):
            if (rate_info.get("exchangeName", "").lower()
                    == exchange.lower()):
                rate = rate_info.get("rate", 0)
                predicted = rate_info.get("predictedRate")
                return {
                    "symbol": symbol.upper(),
                    "exchange": rate_info.get("exchangeName"),
                    "rate": rate,
                    "rate_percent": rate * 100,
                    "next_funding_time": rate_info.get(
                        "nextFundingTime"
                    ),
                    "funding_interval_hours": rate_info.get(
                        "fundingIntervalHours"
                    ),
                    "predicted_rate": predicted,
                    "predicted_rate_percent": (
                        predicted * 100 if predicted else None
                    ),
                }
        return None

    # Average across all exchanges
    rates = [
        r.get("rate", 0)
        for r in symbol_data.get("uMarginList", [])
        if r.get("rate") is not None
    ]
    if not rates:
        return None

    avg_rate = sum(rates) / len(rates)
    return {
        "symbol": symbol.upper(),
        "exchange": "average",
        "rate": avg_rate,
        "rate_percent": avg_rate * 100,
        "num_exchanges": len(rates),
        "exchanges_data": symbol_data.get("uMarginList", []),
    }


def get_funding_rate_by_exchange(
    exchange: str
) -> Optional[List[Dict[str, Any]]]:
    """
    Get funding rates for all symbols on a specific exchange.

    Args:
        exchange: Exchange name (Binance, OKX, etc.)

    Returns:
        List of {symbol, rate, rate_percent} dicts.
    """
    data = get_funding_rates()
    if not data:
        return None

    items = data if isinstance(data, list) else []
    results = []
    for symbol_data in items:
        sym = symbol_data.get("symbol", "")
        for rate_info in symbol_data.get("uMarginList", []):
            if (rate_info.get("exchangeName", "").lower()
                    == exchange.lower()):
                rate = rate_info.get("rate", 0)
                results.append({
                    "symbol": sym,
                    "rate": rate,
                    "rate_percent": rate * 100,
                })
    return results if results else None


def analyze_funding_opportunity(
    symbol: str,
    threshold: float = 0.01
) -> Optional[Dict[str, Any]]:
    """
    Analyze funding rate arbitrage opportunities.

    Finds exchanges with the highest and lowest rates and
    calculates the spread.

    Args:
        symbol: Symbol to analyze.
        threshold: Minimum absolute rate to flag (default 0.01 = 1%).

    Returns:
        Dict with highest, lowest, spread, and opportunity flag.
    """
    data = get_funding_rates(symbol)
    if not data:
        return None

    symbol_data = data[0] if isinstance(data, list) and data else None
    if not symbol_data:
        return None

    rates = []
    for r in symbol_data.get("uMarginList", []):
        rate = r.get("rate")
        if rate is not None:
            rates.append({
                "exchange": r.get("exchangeName"),
                "rate": rate,
                "rate_percent": rate * 100,
            })

    if not rates:
        return None

    rates.sort(key=lambda x: x["rate"])
    highest = rates[-1]
    lowest = rates[0]
    spread = highest["rate"] - lowest["rate"]

    return {
        "symbol": symbol.upper(),
        "highest": highest,
        "lowest": lowest,
        "spread": spread,
        "spread_percent": spread * 100,
        "opportunity": abs(spread) >= threshold,
        "num_exchanges": len(rates),
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Coinglass Funding Rate Tools"
    )
    parser.add_argument("--symbol", "-s", help="Symbol (BTC, ETH)")
    parser.add_argument("--exchange", "-e", help="Exchange name")
    parser.add_argument("--analyze", "-a", action="store_true",
                        help="Analyze arbitrage opportunity")
    parser.add_argument("--all", action="store_true",
                        help="Show all funding rates")
    parser.add_argument("--json", "-j", action="store_true")
    args = parser.parse_args()

    try:
        if args.analyze and args.symbol:
            result = analyze_funding_opportunity(args.symbol)
        elif args.exchange:
            result = get_funding_rate_by_exchange(args.exchange)
        elif args.symbol:
            result = get_symbol_funding_rate(
                args.symbol, args.exchange
            )
        elif args.all:
            result = get_funding_rates()
        else:
            parser.print_help()
            return

        if result:
            print(json.dumps(result, indent=2))
        else:
            print("No data found", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
