#!/usr/bin/env python3
"""
Coinglass Futures Market Module

Provides futures market data: supported coins, exchanges, pairs,
coin-level market data, pair-level data, and OHLC price history.
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional, List

from ._api import cg_request


def get_supported_coins() -> Optional[List[str]]:
    """Get list of coins supported by Coinglass futures data."""
    return cg_request("api/futures/supported-coins")


def get_supported_exchanges() -> Optional[List[Dict[str, Any]]]:
    """Get list of exchanges with supported trading pairs."""
    return cg_request("api/futures/supported-exchange-pairs")


def get_supported_pairs(
    exchange: str = "Binance"
) -> Optional[List[Dict[str, Any]]]:
    """
    Get supported trading pairs for a specific exchange.

    Args:
        exchange: Exchange name (Binance, OKX, Bybit, etc.)
    """
    return cg_request(
        "api/futures/supported-exchange-pairs",
        params={"exchange": exchange}
    )


def get_coins_data(
    symbol: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get futures market data aggregated by coin.

    Args:
        symbol: Optional coin filter (BTC, ETH, etc.)
    """
    params = {}
    if symbol:
        params["symbol"] = symbol
    return cg_request("api/futures/coins-markets", params=params or None)


def get_pair_data(
    symbol: str = "BTC",
    exchange: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get futures market data by trading pair.

    Args:
        symbol: Coin symbol (BTC, ETH, etc.)
        exchange: Optional exchange filter.
    """
    params = {"symbol": symbol}
    if exchange:
        params["exchange"] = exchange
    return cg_request("api/futures/pairs-markets", params=params)


def get_ohlc_history(
    symbol: str = "BTC",
    interval: str = "h4",
    exchange: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get OHLC price history for a futures pair.

    Args:
        symbol: Coin symbol.
        interval: Time interval (m1, m5, m15, h1, h4, h12, h24).
        exchange: Optional exchange filter.
    """
    params = {"symbol": symbol, "interval": interval}
    if exchange:
        params["exchange"] = exchange
    return cg_request("api/futures/price/history", params=params)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Coinglass Futures Market Tools"
    )
    parser.add_argument("action", choices=[
        "coins", "exchanges", "pairs", "market", "ohlc"
    ])
    parser.add_argument("--symbol", "-s", default="BTC")
    parser.add_argument("--exchange", "-e", default=None)
    parser.add_argument("--interval", "-i", default="h4")
    args = parser.parse_args()

    actions = {
        "coins": get_supported_coins,
        "exchanges": get_supported_exchanges,
        "pairs": lambda: get_supported_pairs(args.exchange or "Binance"),
        "market": lambda: get_coins_data(args.symbol),
        "ohlc": lambda: get_ohlc_history(
            args.symbol, args.interval, args.exchange
        ),
    }

    try:
        result = actions[args.action]()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
