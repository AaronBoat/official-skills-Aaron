"""
Wallet info — addresses and chain info.
"""

try:
    from .common import wallet_request
except ImportError:
    from common import wallet_request


async def get_wallet_info() -> dict:
    """Get all wallet addresses for this agent."""
    return await wallet_request("GET", "/agent/wallet")
