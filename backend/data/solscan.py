"""
Solscan cross-check helpers.

Always provides human explorer links. Optional SOLSCAN_API_KEY enables
Pro API token holders (limited sniper proxy via holder list labels when present).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY", "").strip()
PRO_BASE = "https://pro-api.solscan.io/v2.0"


def explorer_links(mint: str, pair_address: str | None = None) -> dict[str, str]:
    links = {
        "solscan_token": f"https://solscan.io/token/{mint}",
        "solscan_holders": f"https://solscan.io/token/{mint}#holders",
        "solscan_transfers": f"https://solscan.io/token/{mint}#transfers",
    }
    if pair_address:
        links["solscan_account"] = f"https://solscan.io/account/{pair_address}"
    return links


async def get_top_holders_pro(mint: str, page_size: int = 20) -> dict[str, Any]:
    """Optional Solscan Pro holders. Returns empty if no API key."""
    if not SOLSCAN_API_KEY:
        return {
            "configured": False,
            "holders": [],
            "error": "SOLSCAN_API_KEY not set",
        }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            r = await client.get(
                f"{PRO_BASE}/token/holders",
                params={"address": mint, "page": 1, "page_size": page_size},
                headers={"token": SOLSCAN_API_KEY, "accept": "application/json"},
            )
            if r.status_code >= 400:
                return {
                    "configured": True,
                    "holders": [],
                    "error": f"Solscan API HTTP {r.status_code}",
                }
            data = r.json()
            items = data.get("data") or data.get("items") or []
            if isinstance(data.get("data"), dict):
                items = data["data"].get("items") or data["data"].get("result") or []
            holders = []
            for h in items[:page_size]:
                if not isinstance(h, dict):
                    continue
                holders.append(
                    {
                        "address": h.get("owner") or h.get("address") or h.get("account"),
                        "amount": h.get("amount") or h.get("balance"),
                        "pct": h.get("percentage") or h.get("percent"),
                        "rank": h.get("rank"),
                    }
                )
            return {"configured": True, "holders": holders, "raw_ok": True}
    except Exception as e:
        return {"configured": True, "holders": [], "error": str(e)}


async def enrich_solscan(mint: str, pair_address: str | None = None) -> dict[str, Any]:
    links = explorer_links(mint, pair_address)
    pro = await get_top_holders_pro(mint)
    return {
        "links": links,
        "pro_holders": pro,
        "note": (
            "Use Solscan holders + transfers tabs to manually verify early buyers / snipers. "
            "Pro API key optional for programmatic top holders."
        ),
    }
