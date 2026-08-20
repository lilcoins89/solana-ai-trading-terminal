"""DexScreener API client for Solana token discovery and market data."""

from __future__ import annotations

import httpx
from typing import Any

BASE = "https://api.dexscreener.com"


async def search_pairs(query: str, limit: int = 20) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{BASE}/latest/dex/search", params={"q": query})
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs") or []
        # Prefer Solana
        sol = [p for p in pairs if p.get("chainId") == "solana"]
        return sol[:limit]


async def get_token_pairs(token_address: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{BASE}/latest/dex/tokens/{token_address}")
        r.raise_for_status()
        data = r.json()
        return data.get("pairs") or []


async def get_pair(chain_id: str, pair_address: str) -> dict[str, Any] | None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{BASE}/latest/dex/pairs/{chain_id}/{pair_address}")
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs") or []
        return pairs[0] if pairs else None


async def latest_token_profiles(limit: int = 30) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{BASE}/token-profiles/latest/v1")
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data[:limit]
        return []


async def boosted_tokens(limit: int = 20) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{BASE}/token-boosts/top/v1")
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data[:limit]
        return []


def normalize_pair(pair: dict[str, Any]) -> dict[str, Any]:
    """Extract clean market snapshot from a DexScreener pair."""
    base = pair.get("baseToken") or {}
    quote = pair.get("quoteToken") or {}
    liquidity = pair.get("liquidity") or {}
    volume = pair.get("volume") or {}
    price_change = pair.get("priceChange") or {}
    txns = pair.get("txns") or {}

    return {
        "chain_id": pair.get("chainId"),
        "dex_id": pair.get("dexId"),
        "pair_address": pair.get("pairAddress"),
        "url": pair.get("url"),
        "base_token": {
            "address": base.get("address"),
            "name": base.get("name"),
            "symbol": base.get("symbol"),
        },
        "quote_token": {
            "address": quote.get("address"),
            "name": quote.get("name"),
            "symbol": quote.get("symbol"),
        },
        "price_usd": _f(pair.get("priceUsd")),
        "price_native": pair.get("priceNative"),
        "liquidity_usd": _f(liquidity.get("usd")),
        "fdv": _f(pair.get("fdv")),
        "market_cap": _f(pair.get("marketCap")),
        "volume": {
            "m5": _f(volume.get("m5")),
            "h1": _f(volume.get("h1")),
            "h6": _f(volume.get("h6")),
            "h24": _f(volume.get("h24")),
        },
        "price_change": {
            "m5": _f(price_change.get("m5")),
            "h1": _f(price_change.get("h1")),
            "h6": _f(price_change.get("h6")),
            "h24": _f(price_change.get("h24")),
        },
        "txns": {
            "m5": txns.get("m5") or {},
            "h1": txns.get("h1") or {},
            "h6": txns.get("h6") or {},
            "h24": txns.get("h24") or {},
        },
        "pair_created_at": pair.get("pairCreatedAt"),
        "info": pair.get("info") or {},
        "boosts": pair.get("boosts") or {},
        "labels": pair.get("labels") or [],
    }


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
