"""
Helius Solana data client.

Uses:
- getTokenLargestAccounts → top holder concentration
- getTokenSupply → total supply / decimals
- getAsset (DAS) → mint_authority, freeze_authority, metadata

Requires HELIUS_API_KEY in env. All functions degrade gracefully when unset.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "").strip()
RPC_URL = (
    f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    if HELIUS_API_KEY
    else ""
)


def helius_configured() -> bool:
    return bool(HELIUS_API_KEY)


async def _rpc(method: str, params: Any) -> dict[str, Any] | None:
    if not HELIUS_API_KEY:
        return None
    payload = {"jsonrpc": "2.0", "id": "sat-terminal", "method": method, "params": params}
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            r = await client.post(RPC_URL, json=payload)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                return None
            return data.get("result")
    except Exception:
        return None


async def get_token_supply(mint: str) -> dict[str, Any] | None:
    """Return {amount, decimals, uiAmount, uiAmountString} or None."""
    result = await _rpc("getTokenSupply", [mint])
    if not result:
        return None
    return result.get("value") or result


async def get_token_largest_accounts(mint: str) -> list[dict[str, Any]]:
    """Up to 20 largest token accounts for mint."""
    result = await _rpc("getTokenLargestAccounts", [mint])
    if not result:
        return []
    return result.get("value") or []


async def get_asset(mint: str) -> dict[str, Any] | None:
    """DAS getAsset — authorities, token_info (mint/freeze authority), supply."""
    result = await _rpc(
        "getAsset",
        {"id": mint, "options": {"showFungible": True}},
    )
    return result


async def get_holder_concentration(mint: str) -> dict[str, Any]:
    """
    Compute top-holder concentration from getTokenLargestAccounts + supply.

    Returns:
      configured, top1_pct, top5_pct, top10_pct, top20_pct,
      largest_accounts (list), supply_ui, decimals, error?
    """
    out: dict[str, Any] = {
        "configured": helius_configured(),
        "top1_pct": None,
        "top5_pct": None,
        "top10_pct": None,
        "top20_pct": None,
        "largest_accounts": [],
        "supply_ui": None,
        "decimals": None,
    }
    if not helius_configured():
        out["error"] = "HELIUS_API_KEY not set"
        return out

    supply = await get_token_supply(mint)
    largest = await get_token_largest_accounts(mint)

    if not supply:
        out["error"] = "Could not fetch token supply"
        return out

    decimals = int(supply.get("decimals") or 0)
    # Prefer uiAmount; fall back to raw amount
    supply_ui = supply.get("uiAmount")
    if supply_ui is None:
        try:
            raw = float(supply.get("amount") or 0)
            supply_ui = raw / (10**decimals) if decimals else raw
        except (TypeError, ValueError):
            supply_ui = 0.0

    out["decimals"] = decimals
    out["supply_ui"] = supply_ui

    if not largest or not supply_ui or supply_ui <= 0:
        out["error"] = "No largest accounts or zero supply"
        return out

    # Normalize account ui amounts
    amounts: list[float] = []
    accounts_out: list[dict[str, Any]] = []
    for acc in largest:
        ui = acc.get("uiAmount")
        if ui is None:
            try:
                ui = float(acc.get("amount") or 0) / (10**decimals)
            except (TypeError, ValueError):
                ui = 0.0
        amounts.append(float(ui))
        accounts_out.append(
            {
                "address": acc.get("address"),
                "ui_amount": float(ui),
                "pct": round(100.0 * float(ui) / supply_ui, 3),
            }
        )

    def _pct(n: int) -> float:
        return round(100.0 * sum(amounts[:n]) / supply_ui, 2)

    out["top1_pct"] = _pct(1)
    out["top5_pct"] = _pct(5)
    out["top10_pct"] = _pct(10)
    out["top20_pct"] = _pct(min(20, len(amounts)))
    out["largest_accounts"] = accounts_out
    return out


async def get_token_authorities(mint: str) -> dict[str, Any]:
    """
    From DAS getAsset token_info:
      mint_authority, freeze_authority, supply, decimals, symbol
    null authority = renounced (safer).
    """
    out: dict[str, Any] = {
        "configured": helius_configured(),
        "mint_authority": None,
        "freeze_authority": None,
        "mint_authority_renounced": None,
        "freeze_authority_renounced": None,
        "supply": None,
        "decimals": None,
        "symbol": None,
        "name": None,
    }
    if not helius_configured():
        out["error"] = "HELIUS_API_KEY not set"
        return out

    asset = await get_asset(mint)
    if not asset:
        out["error"] = "getAsset returned empty"
        return out

    token_info = asset.get("token_info") or {}
    content = asset.get("content") or {}
    meta = content.get("metadata") or {}

    mint_auth = token_info.get("mint_authority")
    freeze_auth = token_info.get("freeze_authority")

    out["mint_authority"] = mint_auth
    out["freeze_authority"] = freeze_auth
    # Renounced when null / missing
    out["mint_authority_renounced"] = mint_auth in (None, "", "null")
    out["freeze_authority_renounced"] = freeze_auth in (None, "", "null")
    out["supply"] = token_info.get("supply")
    out["decimals"] = token_info.get("decimals")
    out["symbol"] = token_info.get("symbol") or meta.get("symbol")
    out["name"] = meta.get("name")
    return out


async def enrich_token(mint: str) -> dict[str, Any]:
    """
    Combined on-chain enrichment for the analysis pipeline.
    Safe to call when Helius is not configured (returns configured=False).
    """
    if not helius_configured():
        return {
            "configured": False,
            "holders": {"configured": False, "error": "HELIUS_API_KEY not set"},
            "authorities": {"configured": False, "error": "HELIUS_API_KEY not set"},
        }

    holders = await get_holder_concentration(mint)
    authorities = await get_token_authorities(mint)
    return {
        "configured": True,
        "holders": holders,
        "authorities": authorities,
    }
