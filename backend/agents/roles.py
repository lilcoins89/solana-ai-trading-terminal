"""
Simplified multi-agent roles adapted from TradingAgents for Solana memecoins.

These are pure functions that take a market snapshot and return text reports.
A later upgrade can replace them with full LangGraph LLM agents.
"""

from __future__ import annotations

from typing import Any


def technical_analyst(market: dict[str, Any]) -> str:
    pc = market.get("price_change") or {}
    vol = market.get("volume") or {}
    signals = []

    h1 = pc.get("h1") or 0
    h24 = pc.get("h24") or 0
    m5 = pc.get("m5") or 0

    if h1 > 15:
        signals.append("Strong 1h momentum (+{:.1f}%)".format(h1))
    elif h1 > 5:
        signals.append("Positive 1h momentum (+{:.1f}%)".format(h1))
    elif h1 < -10:
        signals.append("Selling pressure 1h ({:.1f}%)".format(h1))

    if h24 > 50:
        signals.append("Explosive 24h move (+{:.1f}%)".format(h24))
    elif h24 < -30:
        signals.append("Heavy 24h drawdown ({:.1f}%)".format(h24))

    v24 = vol.get("h24") or 0
    v1 = vol.get("h1") or 0
    if v24 > 500_000 and v1 > 50_000:
        signals.append("Healthy volume profile")
    elif v24 < 20_000:
        signals.append("Very low 24h volume — high manipulation risk")

    if m5 > 8:
        signals.append("Short-term spike in last 5m")

    if not signals:
        signals.append("No strong technical edge detected")

    return "Technical Analyst Report:\n- " + "\n- ".join(signals)


def onchain_risk_analyst(market: dict[str, Any]) -> str:
    liq = market.get("liquidity_usd") or 0
    fdv = market.get("fdv") or market.get("market_cap") or 0
    age_ms = market.get("pair_created_at")
    flags = []

    if liq < 5_000:
        flags.append("CRITICAL: Liquidity under $5k — extreme rug / exit risk")
    elif liq < 25_000:
        flags.append("Low liquidity (<$25k) — high slippage and rug risk")
    elif liq < 100_000:
        flags.append("Moderate liquidity")
    else:
        flags.append("Acceptable liquidity for small size")

    if fdv and liq and fdv > 0:
        ratio = liq / fdv
        if ratio < 0.02:
            flags.append("Very low liquidity/FDV ratio — thin book")

    if age_ms:
        # rough age in hours
        import time
        age_h = (time.time() * 1000 - age_ms) / 3_600_000
        if age_h < 1:
            flags.append("Brand new pair (<1h) — highest risk")
        elif age_h < 6:
            flags.append("Very young pair (<6h)")
        elif age_h < 24:
            flags.append("Young pair (<24h)")

    flags.append("Note: Full holder concentration, mint authority, LP lock require extra APIs (Helius/Birdeye/RugCheck). Always verify manually.")

    return "On-chain / Holder Risk Analyst Report:\n- " + "\n- ".join(flags)


def sentiment_analyst(market: dict[str, Any]) -> str:
    info = market.get("info") or {}
    socials = info.get("socials") or []
    boosts = market.get("boosts") or {}
    active_boosts = boosts.get("active") or 0

    notes = []
    if socials:
        notes.append(f"Token has {len(socials)} linked social(s)")
    else:
        notes.append("No socials linked on DexScreener — higher unknown risk")

    if active_boosts > 0:
        notes.append(f"Active DexScreener boosts: {active_boosts} (paid promotion)")

    notes.append("Social sentiment is approximate without live X/Twitter or Telegram scraping.")
    return "Sentiment Analyst Report:\n- " + "\n- ".join(notes)


def narrative_analyst(market: dict[str, Any]) -> str:
    base = market.get("base_token") or {}
    name = base.get("name") or "Unknown"
    symbol = base.get("symbol") or "???"
    labels = market.get("labels") or []

    notes = [
        f"Token: {name} ({symbol})",
        f"DEX: {market.get('dex_id')}",
    ]
    if labels:
        notes.append(f"Labels: {', '.join(labels)}")
    notes.append("Narrative strength requires external news / CT context.")
    return "Narrative / News Analyst Report:\n- " + "\n- ".join(notes)


def bull_researcher(reports: dict[str, str]) -> str:
    return (
        "Bull Researcher:\n"
        "- Looks for momentum, rising volume, and acceptable liquidity.\n"
        "- Favors tokens that are already showing organic interest.\n"
        "- Accepts higher risk only when volume and liquidity support it."
    )


def bear_researcher(reports: dict[str, str]) -> str:
    return (
        "Bear Researcher:\n"
        "- Emphasizes rug risk, low liquidity, young age, and paid boosts.\n"
        "- Most new Solana tokens fail; default posture is skepticism.\n"
        "- Requires strong evidence before any BUY recommendation."
    )


def trader_agent(reports: dict[str, str], market: dict[str, Any]) -> str:
    return (
        "Trader Agent:\n"
        "- Synthesizes all analyst and researcher views.\n"
        "- Prefers clear risk/reward and defined invalidation (stop).\n"
        "- Size must be tiny relative to portfolio on new tokens."
    )


def risk_manager(reports: dict[str, str], market: dict[str, Any]) -> str:
    liq = market.get("liquidity_usd") or 0
    if liq < 10_000:
        return "Risk Manager: REJECT or AVOID — liquidity too low for safe entry/exit."
    if liq < 50_000:
        return "Risk Manager: Only micro size allowed. Hard stop required. High chance of total loss."
    return "Risk Manager: Liquidity acceptable for very small position. Strict risk limits apply."
