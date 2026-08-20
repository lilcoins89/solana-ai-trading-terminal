"""
Multi-agent roles adapted from TradingAgents for Solana memecoins.
"""

from __future__ import annotations

import time
from typing import Any


def _age_hours(pair_created_at: Any) -> float | None:
    if not pair_created_at:
        return None
    try:
        return (time.time() * 1000 - float(pair_created_at)) / 3_600_000
    except (TypeError, ValueError):
        return None


def _txn_pressure(txns: dict) -> tuple[float, float, float]:
    h1 = txns.get("h1") or {}
    h24 = txns.get("h24") or {}
    b1, s1 = float(h1.get("buys") or 0), float(h1.get("sells") or 0)
    b24, s24 = float(h24.get("buys") or 0), float(h24.get("sells") or 0)
    total1 = b1 + s1
    total24 = b24 + s24
    r1 = b1 / total1 if total1 > 0 else 0.5
    r24 = b24 / total24 if total24 > 0 else 0.5
    return r1, r24, total1


def technical_analyst(market: dict[str, Any]) -> str:
    pc = market.get("price_change") or {}
    vol = market.get("volume") or {}
    txns = market.get("txns") or {}
    signals: list[str] = []

    m5 = float(pc.get("m5") or 0)
    h1 = float(pc.get("h1") or 0)
    h6 = float(pc.get("h6") or 0)
    h24 = float(pc.get("h24") or 0)
    v1 = float(vol.get("h1") or 0)
    v6 = float(vol.get("h6") or 0)
    v24 = float(vol.get("h24") or 0)
    buy_r1, _, tx_h1 = _txn_pressure(txns)

    if h1 > 20 and h6 > 10:
        signals.append(f"Strong multi-timeframe momentum (1h {h1:+.1f}%, 6h {h6:+.1f}%)")
    elif h1 > 10:
        signals.append(f"Solid 1h momentum ({h1:+.1f}%)")
    elif h1 > 3:
        signals.append(f"Mild positive 1h drift ({h1:+.1f}%)")
    elif h1 < -15:
        signals.append(f"Heavy 1h selling ({h1:+.1f}%)")
    elif h1 < -5:
        signals.append(f"Negative 1h pressure ({h1:+.1f}%)")

    if h24 > 80:
        signals.append(f"Parabolic 24h move ({h24:+.1f}%) — late-entry risk")
    elif h24 > 30:
        signals.append(f"Strong 24h trend ({h24:+.1f}%)")
    elif h24 < -40:
        signals.append(f"Severe 24h drawdown ({h24:+.1f}%)")

    if v24 > 1_000_000 and v1 > 80_000:
        signals.append(f"High-quality volume (24h ${v24:,.0f}, 1h ${v1:,.0f})")
    elif v24 > 250_000:
        signals.append(f"Decent volume (24h ${v24:,.0f})")
    elif v24 < 15_000:
        signals.append("Extremely low volume — easy to manipulate")

    if v1 > 0 and v6 > 0 and v1 > (v6 / 6) * 2.5:
        signals.append("Volume accelerating vs 6h average")

    if buy_r1 >= 0.62 and tx_h1 >= 40:
        signals.append(f"Buy-side dominance 1h ({buy_r1*100:.0f}% buys, {tx_h1:.0f} tx)")
    elif buy_r1 <= 0.38 and tx_h1 >= 40:
        signals.append(f"Sell-side dominance 1h ({(1-buy_r1)*100:.0f}% sells)")

    if m5 > 12:
        signals.append(f"Sharp 5m spike (+{m5:.1f}%) — possible FOMO candle")
    elif m5 < -10:
        signals.append(f"Sharp 5m dump ({m5:+.1f}%)")

    if not signals:
        signals.append("No clear technical edge")

    return "Technical Analyst Report:\n- " + "\n- ".join(signals)


def onchain_risk_analyst(
    market: dict[str, Any],
    helius: dict[str, Any] | None = None,
    cross: dict[str, Any] | None = None,
) -> str:
    liq = float(market.get("liquidity_usd") or 0)
    fdv = float(market.get("fdv") or market.get("market_cap") or 0)
    age_h = _age_hours(market.get("pair_created_at"))
    flags: list[str] = []

    if liq < 3_000:
        flags.append("CRITICAL liquidity (<$3k)")
    elif liq < 10_000:
        flags.append("Very low liquidity (<$10k)")
    elif liq < 30_000:
        flags.append("Low liquidity (<$30k)")
    elif liq < 100_000:
        flags.append("Moderate liquidity")
    else:
        flags.append(f"Healthy liquidity (${liq:,.0f})")

    if fdv > 0 and liq > 0:
        ratio = liq / fdv
        if ratio < 0.015:
            flags.append(f"Dangerously thin book (liq/FDV {ratio*100:.2f}%)")
        elif ratio < 0.04:
            flags.append(f"Thin liquidity vs FDV ({ratio*100:.2f}%)")

    if age_h is not None:
        if age_h < 0.5:
            flags.append("Brand-new pair (<30m)")
        elif age_h < 2:
            flags.append(f"Very young pair ({age_h:.1f}h)")
        elif age_h < 24:
            flags.append(f"Young pair ({age_h:.1f}h)")

    helius = helius or {}
    holders = helius.get("holders") or {}
    authorities = helius.get("authorities") or {}

    if helius.get("configured"):
        top1, top10, top20 = holders.get("top1_pct"), holders.get("top10_pct"), holders.get("top20_pct")
        if top10 is not None:
            flags.append(f"Helius concentration: top1={top1}% top10={top10}% top20={top20}%")
            if top1 is not None and top1 >= 30:
                flags.append("CRITICAL: single wallet ≥30%")
            if top10 >= 70:
                flags.append("CRITICAL: top-10 ≥70%")
        mint_ren = authorities.get("mint_authority_renounced")
        freeze_ren = authorities.get("freeze_authority_renounced")
        if mint_ren is True:
            flags.append("Mint authority RENNOUNCED")
        elif mint_ren is False:
            flags.append("Mint authority ACTIVE")
        if freeze_ren is True:
            flags.append("Freeze authority RENNOUNCED")
        elif freeze_ren is False:
            flags.append("Freeze authority ACTIVE")
    else:
        flags.append("Helius not configured (optional)")

    # RugCheck / Solscan cross-check
    cross = cross or {}
    rug = cross.get("rugcheck") or {}
    sol = cross.get("solscan") or {}
    if rug.get("ok"):
        lp = rug.get("lp_locked_pct")
        if lp is not None:
            flags.append(f"RugCheck LP locked: {lp}%")
            if lp < 10:
                flags.append("CRITICAL: LP mostly unlocked — high rug risk")
            elif lp < 50:
                flags.append("LP only partially locked")
        if rug.get("sniper_or_insider_suspected"):
            flags.append("RugCheck risk names suggest sniper/insider/bundle activity")
        for r in (rug.get("risks") or [])[:5]:
            if isinstance(r, dict):
                flags.append(f"RugCheck [{r.get('level')}]: {r.get('name')}")
    else:
        flags.append(f"RugCheck: {rug.get('error') or 'unavailable'}")

    links = {**(rug.get("links") or {}), **(sol.get("links") or {})}
    if links.get("rugcheck"):
        flags.append(f"Cross-check RugCheck: {links['rugcheck']}")
    if links.get("solscan_holders") or links.get("solscan_token"):
        flags.append(
            f"Cross-check Solscan holders: {links.get('solscan_holders') or links.get('solscan_token')}"
        )

    return "On-chain / Holder Risk Analyst Report:\n- " + "\n- ".join(flags)


def sentiment_analyst(market: dict[str, Any]) -> str:
    info = market.get("info") or {}
    socials = info.get("socials") or []
    boosts = market.get("boosts") or {}
    active = int(boosts.get("active") or 0)
    notes: list[str] = []
    if socials:
        notes.append(f"Linked socials: {len(socials)}")
    else:
        notes.append("No socials on DexScreener")
    notes.append(f"Paid boosts: {active}" if active else "No paid boosts")
    pc = market.get("price_change") or {}
    h1 = float(pc.get("h1") or 0)
    buy_r1, _, tx_h1 = _txn_pressure(market.get("txns") or {})
    if h1 > 8 and buy_r1 > 0.58 and tx_h1 > 30:
        notes.append("Proxy sentiment: bullish")
    elif h1 < -8 and buy_r1 < 0.42:
        notes.append("Proxy sentiment: bearish")
    else:
        notes.append("Proxy sentiment: mixed / neutral")
    return "Sentiment Analyst Report:\n- " + "\n- ".join(notes)


def narrative_analyst(market: dict[str, Any]) -> str:
    base = market.get("base_token") or {}
    name = base.get("name") or "Unknown"
    symbol = base.get("symbol") or "???"
    notes = [f"Token: {name} ({symbol})", f"DEX: {market.get('dex_id')}"]
    return "Narrative / News Analyst Report:\n- " + "\n- ".join(notes)


def bull_researcher(reports: dict[str, str], market: dict[str, Any]) -> str:
    liq = float(market.get("liquidity_usd") or 0)
    h1 = float((market.get("price_change") or {}).get("h1") or 0)
    vol24 = float((market.get("volume") or {}).get("h24") or 0)
    points = []
    if h1 > 5:
        points.append(f"Positive 1h momentum ({h1:+.1f}%)")
    if vol24 > 200_000:
        points.append(f"Volume ${vol24:,.0f}")
    if liq >= 50_000:
        points.append(f"Liquidity ${liq:,.0f}")
    if not points:
        points.append("Limited constructive evidence")
    return "Bull Researcher:\n- " + "\n- ".join(points)


def bear_researcher(
    reports: dict[str, str],
    market: dict[str, Any],
    helius: dict[str, Any] | None = None,
    cross: dict[str, Any] | None = None,
) -> str:
    liq = float(market.get("liquidity_usd") or 0)
    age_h = _age_hours(market.get("pair_created_at"))
    helius = helius or {}
    cross = cross or {}
    rug = cross.get("rugcheck") or {}
    holders = helius.get("holders") or {}
    points = ["Most Solana memecoins trend to zero."]
    if liq < 30_000:
        points.append(f"Liquidity ${liq:,.0f} below safety threshold")
    if age_h is not None and age_h < 6:
        points.append(f"Young pair ({age_h:.1f}h)")
    top10 = holders.get("top10_pct")
    if top10 is not None and top10 >= 50:
        points.append(f"Top-10 control {top10}%")
    lp = rug.get("lp_locked_pct")
    if lp is not None and lp < 50:
        points.append(f"LP only {lp}% locked (RugCheck)")
    if rug.get("sniper_or_insider_suspected"):
        points.append("Sniper/insider signals on RugCheck")
    points.append("Require extraordinary evidence before BUY.")
    return "Bear Researcher:\n- " + "\n- ".join(points)


def trader_agent(reports: dict[str, str], market: dict[str, Any]) -> str:
    return (
        "Trader Agent:\n"
        f"- Spot ~${market.get('price_usd')} | Liq ${float(market.get('liquidity_usd') or 0):,.0f}\n"
        "- Prefer WATCH when LP unlocked or sniper flags present.\n"
        "- Micro size only; never chase 5m candles."
    )


def risk_manager(
    reports: dict[str, str],
    market: dict[str, Any],
    helius: dict[str, Any] | None = None,
    cross: dict[str, Any] | None = None,
) -> str:
    liq = float(market.get("liquidity_usd") or 0)
    age_h = _age_hours(market.get("pair_created_at"))
    vol24 = float((market.get("volume") or {}).get("h24") or 0)
    helius = helius or {}
    cross = cross or {}
    rug = cross.get("rugcheck") or {}
    holders = helius.get("holders") or {}
    authorities = helius.get("authorities") or {}
    top1 = holders.get("top1_pct")
    top10 = holders.get("top10_pct")
    lp = rug.get("lp_locked_pct")

    if lp is not None and lp < 5 and liq < 250_000:
        return (
            "Risk Manager: HARD AVOID — LP essentially unlocked (RugCheck). "
            "Classic rug setup. Verify on RugCheck + Solscan."
        )
    if rug.get("sniper_or_insider_suspected") and (lp is None or lp < 60):
        return (
            "Risk Manager: AVOID — sniper/insider signals with weak LP lock. "
            "Inspect Solscan first buyers / transfers."
        )
    if top10 is not None and top10 >= 75:
        return "Risk Manager: HARD AVOID — top-10 ≥75%."
    if top1 is not None and top1 >= 40:
        return "Risk Manager: HARD AVOID — single wallet ≥40%."
    if authorities.get("mint_authority_renounced") is False and liq < 150_000:
        return "Risk Manager: AVOID — mint authority active."
    if liq < 8_000:
        return "Risk Manager: HARD AVOID — liquidity too low."
    if liq < 25_000:
        return "Risk Manager: AVOID or micro paper only."
    if age_h is not None and age_h < 1 and liq < 80_000:
        return "Risk Manager: REJECT — extremely young + modest liquidity."
    if vol24 < 20_000:
        return "Risk Manager: Volume too thin — skip."
    if top10 is not None and top10 >= 55:
        return "Risk Manager: Elevated concentration — micro only / WATCH."
    if liq < 80_000:
        return "Risk Manager: Conditional micro size only. Invalidation required."
    return "Risk Manager: Small tactical size only. Enforce stops. No averaging into rugs."
