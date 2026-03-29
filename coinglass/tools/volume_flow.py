#!/usr/bin/env python3
"""
Coinglass Volume & Flow Module

Provides taker volume history, aggregated taker volume,
cumulative volume delta (CVD), coin netflow, and vol-weighted OHLC.
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional, List

from ._api import cg_request


def _to_pair(symbol: str) -> str:
    """Convert symbol to trading pair (BTC → BTCUSDT)."""
    s = symbol.upper()
    return s if s.endswith("USDT") else f"{s}USDT"


def get_taker_volume_history(
    symbol: str = "BTC",
    exchange: str = "Binance",
    interval: str = "1h"
) -> Optional[List[Dict[str, Any]]]:
    """
    Get taker buy/sell volume history for a coin.

    Args:
        symbol: Coin symbol.
        interval: Time interval (h1, h4, h12, h24).
        exchange: Optional exchange filter.
    """
    return cg_request(
        "api/futures/v2/taker-buy-sell-volume/history",
        params={
            "symbol": _to_pair(symbol),
            "exchange": exchange,
            "interval": interval,
        }
    )


def get_aggregated_taker_volume(
    symbol: str = "BTC",
    interval: str = "h4"
) -> Optional[List[Dict[str, Any]]]:
    """
    Get aggregated taker buy/sell volume history across exchanges.

    Args:
        symbol: Coin symbol.
        interval: Time interval.
    """
    return cg_request(
        "api/futures/aggregated-taker-buy-sell-volume/history",
        params={"symbol": _to_pair(symbol), "interval": interval}
    )


def get_cumulative_volume_delta(
    symbol: str = "BTC",
    exchange: str = "Binance",
    interval: str = "1h"
) -> Optional[List[Dict[str, Any]]]:
    """
    Get cumulative volume delta (CVD) history.

    CVD tracks net buying vs selling pressure over time.

    Args:
        symbol: Coin symbol.
        interval: Time interval.
        exchange: Optional exchange filter.
    """
    return cg_request(
        "api/futures/cvd/history",
        params={
            "symbol": _to_pair(symbol),
            "exchange": exchange,
            "interval": interval,
        }
    )


def get_coin_netflow(
    symbol: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get exchange netflow data by coin.

    Shows net inflow/outflow of coins across exchanges.

    Args:
        symbol: Optional coin filter.
    """
    params = {}
    if symbol:
        params["symbol"] = symbol
    return cg_request("api/futures/netflow-list", params=params or None)


def get_volume_ohlc_history(
    symbol: str = "BTC",
    exchange: str = "Binance",
    interval: str = "1h"
) -> Optional[List[Dict[str, Any]]]:
    """
    Get volume-weighted OHLC history.

    Args:
        symbol: Coin symbol.
        interval: Time interval.
        exchange: Optional exchange filter.
    """
    return cg_request(
        "api/futures/vol-weight-ohlc-history",
        params={
            "symbol": _to_pair(symbol),
            "exchange": exchange,
            "interval": interval,
        }
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Coinglass Volume & Flow Tools"
    )
    parser.add_argument("action", choices=[
        "taker", "aggregated", "cvd", "netflow", "ohlc"
    ])
    parser.add_argument("--symbol", "-s", default="BTC")
    parser.add_argument("--exchange", "-e", default=None)
    parser.add_argument("--interval", "-i", default="h4")
    args = parser.parse_args()

    actions = {
        "taker": lambda: get_taker_volume_history(
            args.symbol, args.exchange or "Binance", args.interval
        ),
        "aggregated": lambda: get_aggregated_taker_volume(
            args.symbol, args.interval
        ),
        "cvd": lambda: get_cumulative_volume_delta(
            args.symbol, args.exchange or "Binance", args.interval
        ),
        "netflow": lambda: get_coin_netflow(args.symbol),
        "ohlc": lambda: get_volume_ohlc_history(
            args.symbol, args.exchange or "Binance", args.interval
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
