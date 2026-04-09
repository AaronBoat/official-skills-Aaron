"""
Wallet skill exports — for use in task scripts via core.skill_tools.

Usage:
    from core.skill_tools import wallet
    info = wallet.wallet_info()
    bal = wallet.wallet_balance(chain="base")
    all_bal = wallet.wallet_get_all_balances()
"""

import asyncio

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

try:
    # skill_tools loads this standalone — bare imports
    from common import is_fly_machine, wallet_request, get_wallet_addresses
    from info import get_wallet_info as _get_info
    from balance import get_evm_balance as _get_evm_bal, get_sol_balance as _get_sol_bal, get_all_balances as _get_all
    from transfer import (
        evm_transfer as _evm_transfer,
        evm_sign_transaction as _evm_sign_tx,
        evm_sign_message as _evm_sign_msg,
        evm_sign_typed_data as _evm_sign_typed,
        evm_transactions as _evm_txs,
        sol_transfer as _sol_transfer,
        sol_sign_transaction as _sol_sign_tx,
        sol_sign_message as _sol_sign_msg,
        sol_transactions as _sol_txs,
    )
    from policy import get_policy as _get_policy
except ImportError:
    # Direct package import — relative imports
    from .tools.common import is_fly_machine, wallet_request, get_wallet_addresses
    from .tools.info import get_wallet_info as _get_info
    from .tools.balance import get_evm_balance as _get_evm_bal, get_sol_balance as _get_sol_bal, get_all_balances as _get_all
    from .tools.transfer import (
        evm_transfer as _evm_transfer,
        evm_sign_transaction as _evm_sign_tx,
        evm_sign_message as _evm_sign_msg,
        evm_sign_typed_data as _evm_sign_typed,
        evm_transactions as _evm_txs,
        sol_transfer as _sol_transfer,
        sol_sign_transaction as _sol_sign_tx,
        sol_sign_message as _sol_sign_msg,
        sol_transactions as _sol_txs,
    )
    from .tools.policy import get_policy as _get_policy


def _run(coro):
    """Run async in sync context (works even if event loop is running)."""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── Info ─────────────────────────────────────────────────────────────────────

def wallet_info():
    """Get all wallet addresses."""
    return _run(_get_info())


# ── Balances ─────────────────────────────────────────────────────────────────

def wallet_balance(chain: str, address: str = "", asset: str = ""):
    """Get EVM balance on a chain."""
    return _run(_get_evm_bal(chain, address, asset))

def wallet_sol_balance(address: str = "", asset: str = ""):
    """Get Solana balance."""
    return _run(_get_sol_bal(address, asset))

def wallet_get_all_balances(evm_address: str = "", sol_address: str = ""):
    """Get balances across all chains."""
    return _run(_get_all(evm_address, sol_address))


# ── Transfers ────────────────────────────────────────────────────────────────

def wallet_transfer(to, amount, chain_id=1, data="", **kw):
    """Sign and broadcast EVM tx."""
    return _run(_evm_transfer(to, amount, chain_id, data, **kw))

def wallet_sign_transaction(to, amount, chain_id=1, data="", **kw):
    """Sign EVM tx without broadcasting."""
    return _run(_evm_sign_tx(to, amount, chain_id, data, **kw))

def wallet_sign(message):
    """EIP-191 personal_sign."""
    return _run(_evm_sign_msg(message))

def wallet_sign_typed_data(domain, types, primaryType, message):
    """Sign EIP-712 typed data."""
    return _run(_evm_sign_typed(domain, types, primaryType, message))

def wallet_transactions(chain="ethereum", asset="", limit=20):
    """EVM tx history. Asset auto-detected from chain if empty."""
    return _run(_evm_txs(chain, asset, limit))


# ── Solana ───────────────────────────────────────────────────────────────────

def wallet_sol_transfer(transaction, rpc_url="https://api.mainnet-beta.solana.com"):
    """Sign and broadcast Solana tx (no gas sponsorship — user pays gas)."""
    return _run(_sol_transfer(transaction, rpc_url))

def wallet_sol_sign_transaction(transaction):
    """Sign Solana tx without broadcasting."""
    return _run(_sol_sign_tx(transaction))

def wallet_sol_sign(message):
    """Sign message with Solana wallet."""
    return _run(_sol_sign_msg(message))

def wallet_sol_transactions(chain="solana", asset="sol", limit=20):
    """Solana tx history."""
    return _run(_sol_txs(chain, asset, limit))


# ── Policy ───────────────────────────────────────────────────────────────────

def wallet_get_policy(chain_type="ethereum"):
    """Get current policy status."""
    return _run(_get_policy(chain_type))
