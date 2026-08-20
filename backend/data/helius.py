"""Helius Solana data client (holders, supply, mint/freeze authority)."""

from __future__ import annotations

import os
from typing import Any

import httpx


def _api_key() -> str:
    return os.getenv("HELIUS_API_KEY", "").strip()


def helius_configured() -> bool:
    return bool(_api_key())


def _rpc_url() -> str:
    key = _api_key()
    return f"https://mainnet.helius-rpc.com/?api-key={key}" if key else ""


async def _rpc(method: str, params: Any) -> dict[str, Any] | None:
    if not _api_key():
        return None
    payload = {"jsonrpc": "2.0", "id": "sat-terminal", "method": method, "params": params}
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            r = await client.post(_rpc_url(), json=payload)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                return None
            return data.get("result")
    except Exception:
        return None


async def get_token_supply(mint: str) -> dict[str, Any] | None:
    result = await _rpc("getTokenSupply", [mint])
    if not result:
        return None
    return result.get("value") or result


async def get_token_largest_accounts(mint: str) -> list[dict[str, Any]]:
    result = await _rpc("getTokenLargestAccounts", [mint])
    if not result:
        return []
    return result.get("value") or []


async def get_asset(mint: str) -> dict[str, Any] | None:
    return await _rpc("getAsset", {"id": mint, "options": {"showFungible": True}})


async def get_holder_concentration(mint: str) -> dict[str, Any]:
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
    meta = (asset.get("content") or {}).get("metadata") or {}
    mint_auth = token_info.get("mint_authority")
    freeze_auth = token_info.get("freeze_authority")

    out["mint_authority"] = mint_auth
    out["freeze_authority"] = freeze_auth
    out["mint_authority_renounced"] = mint_auth in (None, "", "null")
    out["freeze_authority_renounced"] = freeze_auth in (None, "", "null")
    out["supply"] = token_info.get("supply")
    out["decimals"] = token_info.get("decimals")
    out["symbol"] = token_info.get("symbol") or meta.get("symbol")
    out["name"] = meta.get("name")
    return out


async def enrich_token(mint: str) -> dict[str, Any]:
    if not helius_configured():
        return {
            "configured": False,
            "holders": {"configured": False, "error": "HELIUS_API_KEY not set"},
            "authorities": {"configured": False, "error": "HELIUS_API_KEY not set"},
        }
    holders = await get_holder_concentration(mint)
    authorities = await get_token_authorities(mint)
    return {"configured": True, "holders": holders, "authorities": authorities}
