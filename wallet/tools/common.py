"""
Wallet Tools — shared infrastructure.

Auth: Fly OIDC tokens from /.fly/api Unix Socket.
Each machine has one wallet per chain_type (ethereum, solana).
"""

import asyncio
import logging
import os
import time
from typing import Optional

import aiohttp

# ── Fix aiohttp 3.13.x + Brotli 1.1.0 incompatibility ──────────────────────
try:
    from typing import cast
    import aiohttp.compression_utils as _cu
    _orig = getattr(_cu.BrotliDecompressor, 'decompress_sync', None)
    if _orig:
        def _fixed_decompress_sync(self, data, max_length=0):
            if hasattr(self._obj, 'decompress'):
                return cast(bytes, self._obj.decompress(data))
            return cast(bytes, self._obj.process(data))
        _cu.BrotliDecompressor.decompress_sync = _fixed_decompress_sync
except Exception:
    pass

import requests
from core.http_client import proxied_get

logger = logging.getLogger(__name__)

WALLET_SERVICE_URL = os.environ.get(
    "WALLET_SERVICE_URL", "https://wallet-service-dev.fly.dev"
)
OIDC_AUDIENCE = os.environ.get("WALLET_OIDC_AUDIENCE", WALLET_SERVICE_URL)
FLY_API_SOCKET = "/.fly/api"

DEBANK_CHAIN_MAP = {
    "ethereum": "eth", "base": "base", "arbitrum": "arb",
    "optimism": "op", "polygon": "matic", "linea": "linea",
}

EVM_CHAINS = list(DEBANK_CHAIN_MAP.keys())

# ── OIDC token cache ─────────────────────────────────────────────────────────
_cached_token: Optional[str] = None
_cached_token_exp: float = 0


async def _fetch_oidc_token() -> str:
    conn = aiohttp.UnixConnector(path=FLY_API_SOCKET)
    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.post(
            "http://localhost/v1/tokens/oidc",
            json={"aud": OIDC_AUDIENCE},
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            resp.raise_for_status()
            return (await resp.text()).strip()


async def ensure_token() -> str:
    global _cached_token, _cached_token_exp
    if not _cached_token or time.time() > _cached_token_exp - 120:
        _cached_token = await _fetch_oidc_token()
        _cached_token_exp = time.time() + 600
    return _cached_token


def is_fly_machine() -> bool:
    return os.path.exists(FLY_API_SOCKET)


async def wallet_request(method: str, path: str, json_body: dict = None) -> dict:
    """Authenticated request to privy-wallet Agent API."""
    token = await ensure_token()
    headers = {"Authorization": f"Bearer {token}", "Accept-Encoding": "gzip, deflate"}
    url = f"{WALLET_SERVICE_URL}{path}"

    async with aiohttp.ClientSession() as session:
        async with session.request(
            method, url,
            headers=headers,
            json=json_body if method in ("POST", "PUT", "PATCH") else None,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            body = await resp.json()
            if resp.status >= 400:
                detail = body.get("detail") or body.get("error") or str(body)
                raise Exception(f"Wallet service error ({resp.status}): {detail}")
            return body


# ── Wallet address cache ─────────────────────────────────────────────────────
_addr_cache: dict = {}
_addr_cache_exp: float = 0


async def get_wallet_addresses() -> dict:
    """Return {"evm": "0x...", "sol": "..."} from wallet service, cached 5 min."""
    global _addr_cache, _addr_cache_exp
    if _addr_cache and time.time() < _addr_cache_exp:
        return _addr_cache

    data = await wallet_request("GET", "/agent/wallet")
    wallets = data if isinstance(data, list) else data.get("wallets", [])
    result = {}
    for w in wallets:
        if not isinstance(w, dict):
            continue
        ct = w.get("chain_type", "")
        addr = w.get("wallet_address", "") or w.get("address", "")
        if ct == "ethereum" and addr and "evm" not in result:
            result["evm"] = addr
        elif ct == "solana" and addr and "sol" not in result:
            result["sol"] = addr
    _addr_cache = result
    _addr_cache_exp = time.time() + 300
    return result


def proxied_get_with_retry(url, params=None, headers=None, timeout=30, max_retries=3):
    """proxied_get with retry on timeout / 429 / 5xx."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = proxied_get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.Timeout as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(1)
        except requests.exceptions.HTTPError:
            raise
        except Exception as e:
            last_exc = e
            break
    raise last_exc or requests.exceptions.RequestException("Max retries exceeded")
