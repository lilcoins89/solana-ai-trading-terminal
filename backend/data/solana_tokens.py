from __future__ import annotations

import asyncio
from typing import Any

from data.dexscreener import latest_token_profiles, get_token_pairs, normalize_pair
from data.helius import get_asset, get_token_supply, helius_configured


async def solana_token_feed(limit: int = 12) -> list[dict[str, Any]]:
    """Return Solana-only market data from DexScreener plus token facts from Helius."""
    profiles = await latest_token_profiles(limit=max(limit * 3, 25))
    sol_profiles = [p for p in profiles if p.get("chainId") == "solana"]

    async def hydrate(profile: dict[str, Any]) -> dict[str, Any] | None:
        mint = profile.get("tokenAddress")
        if not mint:
            return None
        try:
            pairs = await get_token_pairs(mint)
            pairs = [p for p in pairs if p.get("chainId") == "solana"]
            market = normalize_pair(max(pairs, key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0))) if pairs else {}
        except Exception:
            market = {}
        helius: dict[str, Any] = {}
        asset: dict[str, Any] | None = None
        if helius_configured():
            asset, supply = await asyncio.gather(get_asset(mint), get_token_supply(mint))
            metadata = (asset or {}).get("content", {}).get("metadata", {})
            token_info = (asset or {}).get("token_info", {})
            helius = {"name": metadata.get("name"), "symbol": token_info.get("symbol") or metadata.get("symbol"), "decimals": token_info.get("decimals") or (supply or {}).get("decimals"), "supply": (supply or {}).get("uiAmount") or (supply or {}).get("amount")}
        base = market.get("base_token") or {}
        links = (asset or {}).get("content", {}).get("links", {}) if asset else {}
        image_url = links.get("image") or profile.get("icon")
        if not image_url or not image_url.lower().endswith(".svg"):
            return None
        symbol = helius.get("symbol") or base.get("symbol")
        name = helius.get("name") or base.get("name")
        if not symbol or not name:
            return None
        return {"chain_id": "solana", "token_address": mint, "symbol": symbol, "name": name, "price": market.get("price_usd") or 0, "change_24h": (market.get("price_change") or {}).get("h24") or 0, "volume_24h": (market.get("volume") or {}).get("h24") or 0, "liquidity": market.get("liquidity_usd") or 0, "icon_url": image_url, "profile_url": profile.get("url"), "helius": helius}

    hydrated = await asyncio.gather(*(hydrate(p) for p in sol_profiles[:limit]))
    return [item for item in hydrated if item]
