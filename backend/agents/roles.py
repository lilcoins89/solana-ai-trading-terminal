"""
Multi-agent roles adapted from TradingAgents for Solana memecoins.

Each role returns a structured text report plus contributes signals that the
pipeline aggregates into a final Decision.
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
    """Return (buy_ratio_h1, buy_ratio_h24, total_tx_h1)."""
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

    buy_r1, buy_r24, tx_h1 = _txn_pressure(txns)

    # Momentum structure
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

    # Volume quality
    if v24 > 1_000_000 and v1 > 80_000:
        signals.append(f"High-quality volume (24h ${v24:,.0f}, 1h ${v1:,.0f})")
    elif v24 > 250_000:
        signals.append(f"Decent volume (24h ${v24:,.0f})")
    elif v24 < 15_000:
        signals.append("Extremely low volume — easy to manipulate")

    if v1 > 0 and v6 > 0 and v1 > (v6 / 6) * 2.5:
        signals.append("Volume accelerating vs 6h average")

    # Order-flow proxy
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


def onchain_risk_analyst(market: dict[str, Any]) -> str:
    liq = float(market.get("liquidity_usd") or 0)
    fdv = float(market.get("fdv") or market.get("market_cap") or 0)
    age_h = _age_hours(market.get("pair_created_at"))
    flags: list[str] = []
    score_hints: list[str] = []

    if liq < 3_000:
        flags.append("CRITICAL liquidity (<$3k) — near-certain exit difficulty / rug risk")
    elif liq < 10_000:
        flags.append("Very low liquidity (<$10k) — high slippage & rug risk")
    elif liq < 30_000:
        flags.append("Low liquidity (<$30k) — size carefully")
    elif liq < 100_000:
        flags.append("Moderate liquidity")
        score_hints.append("tradeable_micro")
    else:
        flags.append(f"Healthy liquidity (${liq:,.0f})")
        score_hints.append("tradeable")

    if fdv > 0 and liq > 0:
        ratio = liq / fdv
        if ratio < 0.015:
            flags.append(f"Dangerously thin book (liq/FDV {ratio*100:.2f}%)")
        elif ratio < 0.04:
            flags.append(f"Thin liquidity vs FDV ({ratio*100:.2f}%)")
        else:
            flags.append(f"Reasonable liq/FDV ({ratio*100:.1f}%)")

    if age_h is not None:
        if age_h < 0.5:
            flags.append("Brand-new pair (<30m) — maximum uncertainty")
        elif age_h < 2:
            flags.append(f"Very young pair ({age_h:.1f}h)")
        elif age_h < 12:
            flags.append(f"Young pair ({age_h:.1f}h)")
        elif age_h < 72:
            flags.append(f"Establishing pair ({age_h:.0f}h old)")
        else:
            flags.append(f"Mature pair ({age_h/24:.1f}d)")
            score_hints.append("aged")

    flags.append(
        "Reminder: mint authority, freeze authority, LP lock %, top-10 holder concentration "
        "and sniper/bundle detection require Helius / Birdeye / RugCheck. Always verify."
    )

    return "On-chain / Holder Risk Analyst Report:\n- " + "\n- ".join(flags)


def sentiment_analyst(market: dict[str, Any]) -> str:
    info = market.get("info") or {}
    socials = info.get("socials") or []
    websites = info.get("websites") or []
    boosts = market.get("boosts") or {}
    active = int(boosts.get("active") or 0)
    notes: list[str] = []

    if socials:
        platforms = [s.get("platform") or s.get("type") or "social" for s in socials if isinstance(s, dict)]
        notes.append(f"Linked socials: {', '.join(platforms) if platforms else len(socials)}")
    else:
        notes.append("No socials on DexScreener profile — higher opacity risk")

    if websites:
        notes.append(f"Website(s) linked: {len(websites)}")

    if active > 0:
        notes.append(f"Paid DexScreener boosts active: {active} (promotion, not organic proof)")
    else:
        notes.append("No active paid boosts detected")

    # Soft sentiment proxy from order flow + price
    pc = market.get("price_change") or {}
    h1 = float(pc.get("h1") or 0)
    txns = market.get("txns") or {}
    buy_r1, _, tx_h1 = _txn_pressure(txns)
    if h1 > 8 and buy_r1 > 0.58 and tx_h1 > 30:
        notes.append("Proxy sentiment: bullish (price + buy pressure)")
    elif h1 < -8 and buy_r1 < 0.42:
        notes.append("Proxy sentiment: bearish (price + sell pressure)")
    else:
        notes.append("Proxy sentiment: mixed / neutral")

    notes.append("Live X/Telegram scraping not enabled in this build.")
    return "Sentiment Analyst Report:\n- " + "\n- ".join(notes)


def narrative_analyst(market: dict[str, Any]) -> str:
    base = market.get("base_token") or {}
    name = base.get("name") or "Unknown"
    symbol = base.get("symbol") or "???"
    labels = market.get("labels") or []
    dex = market.get("dex_id") or "unknown"

    notes = [
        f"Token: {name} ({symbol})",
        f"Primary DEX: {dex}",
    ]
    if labels:
        notes.append(f"DexScreener labels: {', '.join(str(l) for l in labels)}")

    # Simple narrative heuristics from name/symbol (very rough)
    blob = f"{name} {symbol}".lower()
    if any(k in blob for k in ("ai", "agent", "gpt", "llm")):
        notes.append("Narrative hint: AI / agent theme (crowded sector — high competition)")
    if any(k in blob for k in ("dog", "cat", "pepe", "meme", "inu")):
        notes.append("Narrative hint: classic meme animal theme")
    if any(k in blob for k in ("trump", "biden", "elon", "musk")):
        notes.append("Narrative hint: political / personality meme (high volatility)")

    notes.append("Deep narrative requires CT (Crypto Twitter) + news context beyond this snapshot.")
    return "Narrative / News Analyst Report:\n- " + "\n- ".join(notes)


def bull_researcher(reports: dict[str, str], market: dict[str, Any]) -> str:
    liq = float(market.get("liquidity_usd") or 0)
    pc = market.get("price_change") or {}
    h1 = float(pc.get("h1") or 0)
    vol24 = float((market.get("volume") or {}).get("h24") or 0)
    buy_r1, _, tx_h1 = _txn_pressure(market.get("txns") or {})

    points = []
    if h1 > 5:
        points.append(f"Positive short-term momentum ({h1:+.1f}% 1h)")
    if vol24 > 200_000:
        points.append(f"Meaningful volume (${vol24:,.0f} 24h)")
    if liq >= 50_000:
        points.append(f"Liquidity supports small entries (${liq:,.0f})")
    if buy_r1 > 0.55 and tx_h1 > 25:
        points.append("Buyers currently outnumber sellers (1h)")
    if not points:
        points.append("Limited constructive evidence in current snapshot")

    return "Bull Researcher:\n- " + "\n- ".join(points) + (
        "\n- Stance: only consider long if risk manager allows micro size and invalidation is clear."
    )


def bear_researcher(reports: dict[str, str], market: dict[str, Any]) -> str:
    liq = float(market.get("liquidity_usd") or 0)
    age_h = _age_hours(market.get("pair_created_at"))
    boosts = int((market.get("boosts") or {}).get("active") or 0)
    pc = market.get("price_change") or {}
    h24 = float(pc.get("h24") or 0)

    points = [
        "Most Solana memecoins trend to zero; prior is failure.",
    ]
    if liq < 30_000:
        points.append(f"Liquidity ${liq:,.0f} is below preferred safety threshold")
    if age_h is not None and age_h < 6:
        points.append(f"Pair age {age_h:.1f}h — incomplete discovery of risk")
    if boosts > 0:
        points.append("Paid boosts present — demand may be artificial")
    if h24 > 100:
        points.append(f"Already up {h24:.0f}% in 24h — asymmetric downside")
    if h24 < -25:
        points.append(f"Already down hard ({h24:+.0f}% 24h) — may be dead")

    points.append("Require extraordinary evidence before any BUY.")
    return "Bear Researcher:\n- " + "\n- ".join(points)


def trader_agent(reports: dict[str, str], market: dict[str, Any]) -> str:
    price = market.get("price_usd")
    liq = float(market.get("liquidity_usd") or 0)
    return (
        "Trader Agent:\n"
        f"- Spot ~${price} | Liquidity ${liq:,.0f}\n"
        "- Goal: only take trades with defined stop, micro size, and favorable flow.\n"
        "- Prefer WATCH over forced BUY when signals conflict.\n"
        "- Execution plan: scale-in only after confirmation; never chase 5m green candles."
    )


def risk_manager(reports: dict[str, str], market: dict[str, Any]) -> str:
    liq = float(market.get("liquidity_usd") or 0)
    age_h = _age_hours(market.get("pair_created_at"))
    vol24 = float((market.get("volume") or {}).get("h24") or 0)

    if liq < 8_000:
        return (
            "Risk Manager: HARD AVOID — liquidity too low for controlled entry/exit. "
            "Probability of total loss elevated."
        )
    if liq < 25_000:
        return (
            "Risk Manager: AVOID or micro paper only. "
            "Max theoretical size << 0.5% of pool. Hard stop mandatory."
        )
    if age_h is not None and age_h < 1 and liq < 80_000:
        return (
            "Risk Manager: Extremely young + modest liquidity — default REJECT. "
            "Wait for age and volume confirmation."
        )
    if vol24 < 20_000:
        return "Risk Manager: Volume too thin — skip."
    if liq < 80_000:
        return (
            "Risk Manager: Conditional micro size only (≤0.5% portfolio, ≤1% of pool). "
            "Invalidation required."
        )
    return (
        "Risk Manager: Liquidity acceptable for small tactical size. "
        "Enforce stop-loss and daily loss limits. No averaging down into rugs."
    )
