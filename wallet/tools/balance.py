"""
Balance tools — EVM (DeBank) + Solana (Birdeye) + all-chains aggregation.
"""

import asyncio
import os

try:
    from .common import (
        is_fly_machine, wallet_request, get_wallet_addresses,
        proxied_get_with_retry, DEBANK_CHAIN_MAP, EVM_CHAINS, logger,
    )
except ImportError:
    from common import (
        is_fly_machine, wallet_request, get_wallet_addresses,
        proxied_get_with_retry, DEBANK_CHAIN_MAP, EVM_CHAINS, logger,
    )


async def get_evm_balance(chain: str, address: str = "", asset: str = "") -> dict:
    """Get EVM wallet balance on a specific chain."""
    if chain not in EVM_CHAINS:
        return {"error": f"Invalid chain '{chain}'. Must be one of: {', '.join(EVM_CHAINS)}"}

    debank_key = os.environ.get("DEBANK_API_KEY", "")

    if debank_key:
        evm_address = address
        if not evm_address:
            if not is_fly_machine():
                return {"error": "No address and not on Fly Machine"}
            addrs = await get_wallet_addresses()
            evm_address = addrs.get("evm", "")
        if not evm_address:
            return {"error": "Could not determine EVM wallet address"}

        debank_chain_id = DEBANK_CHAIN_MAP.get(chain)
        try:
            resp = proxied_get_with_retry(
                "https://pro-openapi.debank.com/v1/user/token_list",
                params={"id": evm_address, "chain_id": debank_chain_id, "is_all": "false"},
                headers={"AccessKey": debank_key},
            )
            return {"address": evm_address, "chain": chain, "tokens": resp.json(), "source": "debank"}
        except Exception as e:
            return {"error": f"DeBank request failed: {e}"}
    else:
        if not is_fly_machine():
            return {"error": "Not on Fly Machine — wallet unavailable"}
        params = [f"chain_type=ethereum&chain={chain}"]
        if asset:
            params.append(f"asset={asset}")
        qs = "?" + "&".join(params)
        return await wallet_request("GET", f"/agent/balance{qs}")


async def get_sol_balance(address: str = "", asset: str = "") -> dict:
    """Get Solana wallet balance."""
    birdeye_key = os.environ.get("BIRDEYE_API_KEY", "")

    if birdeye_key:
        sol_address = address
        if not sol_address:
            if not is_fly_machine():
                return {"error": "No address and not on Fly Machine"}
            addrs = await get_wallet_addresses()
            sol_address = addrs.get("sol", "")
        if not sol_address:
            return {"error": "Could not determine Solana wallet address"}

        try:
            resp = proxied_get_with_retry(
                "https://public-api.birdeye.so/wallet/v2/net-worth",
                params={"wallet": sol_address},
                headers={"X-API-KEY": birdeye_key, "x-chain": "solana", "accept": "application/json"},
            )
            return {"address": sol_address, "source": "birdeye", "data": resp.json()}
        except Exception as e:
            return {"error": f"Birdeye request failed: {e}"}
    else:
        if not is_fly_machine():
            return {"error": "Not on Fly Machine — wallet unavailable"}
        params = ["chain_type=solana"]
        if asset:
            params.append(f"asset={asset}")
        qs = "?" + "&".join(params)
        return await wallet_request("GET", f"/agent/balance{qs}")


async def get_all_balances(evm_address: str = "", sol_address: str = "") -> dict:
    """Get balances across ALL chains concurrently."""
    if not evm_address or not sol_address:
        if is_fly_machine():
            try:
                addrs = await get_wallet_addresses()
                evm_address = evm_address or addrs.get("evm", "")
                sol_address = sol_address or addrs.get("sol", "")
            except Exception:
                pass

    result = {}
    errors = []
    evm_usd = 0.0
    sol_usd = 0.0

    async def _fetch_evm():
        nonlocal evm_usd
        if not evm_address:
            return
        debank_key = os.environ.get("DEBANK_API_KEY", "")
        if not debank_key:
            errors.append("No DEBANK_API_KEY")
            return
        try:
            resp = proxied_get_with_retry(
                "https://pro-openapi.debank.com/v1/user/all_token_list",
                params={"id": evm_address, "is_all": "true"},
                headers={"AccessKey": debank_key},
            )
            tokens = resp.json()
            by_chain = {}
            for t in tokens:
                chain = t.get("chain", "unknown")
                if chain not in by_chain:
                    by_chain[chain] = {"tokens": [], "total_usd": 0.0}
                usd = t.get("price", 0) * t.get("amount", 0)
                by_chain[chain]["tokens"].append(t)
                by_chain[chain]["total_usd"] = round(by_chain[chain]["total_usd"] + usd, 2)
                evm_usd += usd
            result["evm"] = {"address": evm_address, "chains": by_chain, "total_usd": round(evm_usd, 2), "source": "debank"}
        except Exception as e:
            errors.append(f"DeBank: {e}")

    async def _fetch_sol():
        nonlocal sol_usd
        if not sol_address:
            return
        birdeye_key = os.environ.get("BIRDEYE_API_KEY", "")
        if not birdeye_key:
            errors.append("No BIRDEYE_API_KEY")
            return
        try:
            resp = proxied_get_with_retry(
                "https://public-api.birdeye.so/wallet/v2/net-worth",
                params={"wallet": sol_address},
                headers={"X-API-KEY": birdeye_key, "x-chain": "solana", "accept": "application/json"},
            )
            data = resp.json()
            sol_usd = data.get("data", {}).get("totalUsd", 0)
            result["solana"] = {"address": sol_address, "source": "birdeye", "data": data, "total_usd": round(sol_usd, 2)}
        except Exception as e:
            errors.append(f"Birdeye: {e}")

    await asyncio.gather(_fetch_evm(), _fetch_sol())

    result["total_usd_value"] = round(evm_usd + sol_usd, 2)
    if errors:
        result["errors"] = errors

    has_data = "evm" in result or "solana" in result
    if not has_data and errors:
        return {"error": "All balance queries failed: " + "; ".join(errors)}
    return result
