"""RugCheck.xyz client — LP lock, risks, sniper/insider signals."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

import httpx

BASE = "https://api.rugcheck.xyz/v1"
_SNIPER_RE = re.compile(
    r"sniper|snipe|bundle|bundler|insider|wash|sybil|fresh.?wallet|dev.?hold", re.I
)


def _headers() -> dict[str, str]:
    h = {"Accept": "application/json"}
    key = os.getenv("RUGCHECK_API_KEY", "").strip()
    if key:
        h["X-API-KEY"] = key
    return h


async def get_report(mint: str) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(f"{BASE}/tokens/{mint}/report", headers=_headers())
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


async def get_summary(mint: str) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                f"{BASE}/tokens/{mint}/report/summary", headers=_headers()
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


def _extract_lp_locked_pct(report: dict, summary: dict | None) -> float | None:
    if summary and summary.get("lpLockedPct") is not None:
        try:
            return float(summary["lpLockedPct"])
        except (TypeError, ValueError):
            pass
    locked_pcts: list[float] = []
    for m in report.get("markets") or []:
        for key in ("lpLockedPct", "lp_locked_pct", "lockedPct"):
            if m.get(key) is not None:
                try:
                    locked_pcts.append(float(m[key]))
                except (TypeError, ValueError):
                    pass
        lp = m.get("lp") or {}
        if isinstance(lp, dict) and lp.get("lpLockedPct") is not None:
            try:
                locked_pcts.append(float(lp["lpLockedPct"]))
            except (TypeError, ValueError):
                pass
    if locked_pcts:
        return max(locked_pcts)
    if report.get("lpLockedPct") is not None:
        try:
            return float(report["lpLockedPct"])
        except (TypeError, ValueError):
            pass
    return None


def _parse_risks(risks: list) -> tuple[list[dict[str, Any]], list[str], bool]:
    out: list[dict[str, Any]] = []
    flags: list[str] = []
    sniperish = False
    for r in risks or []:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or "")
        level = str(r.get("level") or r.get("severity") or "warn")
        desc = str(r.get("description") or "")
        out.append(
            {
                "name": name,
                "level": level,
                "description": desc,
                "value": r.get("value"),
                "score": r.get("score"),
            }
        )
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        if slug:
            flags.append(f"rugcheck_{slug}")
        if _SNIPER_RE.search(f"{name} {desc}"):
            sniperish = True
            flags.append("sniper_or_insider_signal")
        if level.lower() in ("danger", "critical", "high"):
            flags.append(f"danger_{slug}" if slug else "danger_risk")
    return out, list(dict.fromkeys(flags)), sniperish


def _top_holders_from_report(report: dict) -> list[dict[str, Any]]:
    holders = report.get("topHolders") or report.get("top_holders") or []
    out = []
    for h in holders[:15]:
        if not isinstance(h, dict):
            continue
        pct = h.get("pct") or h.get("percentage") or h.get("share")
        try:
            pct_f = float(pct) if pct is not None else None
        except (TypeError, ValueError):
            pct_f = None
        out.append(
            {
                "address": h.get("address") or h.get("owner") or h.get("account"),
                "pct": pct_f,
                "amount": h.get("amount") or h.get("uiAmount"),
                "insider": h.get("insider"),
            }
        )
    return out


async def enrich_rugcheck(mint: str) -> dict[str, Any]:
    report, summary = await asyncio.gather(get_report(mint), get_summary(mint))

    links = {
        "rugcheck": f"https://rugcheck.xyz/tokens/{mint}",
        "solscan": f"https://solscan.io/token/{mint}",
        "solscan_holders": f"https://solscan.io/token/{mint}#holders",
    }

    if not report and not summary:
        return {
            "configured": True,
            "ok": False,
            "error": "RugCheck report unavailable",
            "lp_locked_pct": None,
            "score": None,
            "score_normalised": None,
            "risks": [],
            "flags": ["rugcheck_unavailable"],
            "sniper_or_insider_suspected": False,
            "top_holders": [],
            "links": links,
        }

    risks_raw = (report or {}).get("risks") or (summary or {}).get("risks") or []
    risks, flags, sniperish = _parse_risks(risks_raw)
    lp_pct = _extract_lp_locked_pct(report or {}, summary)

    score = None
    score_norm = None
    if summary:
        score = summary.get("score")
        score_norm = summary.get("score_normalised") or summary.get("scoreNormalized")
    if report:
        score = score if score is not None else report.get("score")
        score_norm = (
            score_norm if score_norm is not None else report.get("score_normalised")
        )

    if lp_pct is not None:
        if lp_pct < 10:
            flags.append("lp_mostly_unlocked")
        elif lp_pct < 50:
            flags.append("lp_partially_locked")
        else:
            flags.append("lp_majority_locked")

    token = (report or {}).get("token") or {}
    mint_auth = token.get("mintAuthority")
    freeze_auth = token.get("freezeAuthority")

    return {
        "configured": True,
        "ok": True,
        "lp_locked_pct": lp_pct,
        "score": score,
        "score_normalised": score_norm,
        "risks": risks,
        "flags": list(dict.fromkeys(flags)),
        "sniper_or_insider_suspected": sniperish,
        "top_holders": _top_holders_from_report(report or {}),
        "mint_authority": mint_auth,
        "freeze_authority": freeze_auth,
        "mint_authority_renounced": mint_auth in (None, "", "null"),
        "freeze_authority_renounced": freeze_auth in (None, "", "null"),
        "links": links,
    }
