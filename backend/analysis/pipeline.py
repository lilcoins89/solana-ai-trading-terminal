"""Orchestrates the multi-agent analysis pipeline and produces a Decision."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.roles import (
    technical_analyst,
    onchain_risk_analyst,
    sentiment_analyst,
    narrative_analyst,
    bull_researcher,
    bear_researcher,
    trader_agent,
    risk_manager,
)
from analysis.schemas import Decision, HolderRisk, PositionSizing


def run_analysis(market: dict[str, Any]) -> Decision:
    """Run the full agent pipeline on a normalized market snapshot."""

    reports = {
        "technical": technical_analyst(market),
        "onchain_risk": onchain_risk_analyst(market),
        "sentiment": sentiment_analyst(market),
        "narrative": narrative_analyst(market),
    }
    reports["bull"] = bull_researcher(reports)
    reports["bear"] = bear_researcher(reports)
    reports["trader"] = trader_agent(reports, market)
    reports["risk"] = risk_manager(reports, market)

    # --- Deterministic scoring ---
    liq = market.get("liquidity_usd") or 0.0
    vol24 = (market.get("volume") or {}).get("h24") or 0.0
    pc = market.get("price_change") or {}
    h1 = pc.get("h1") or 0.0
    h24 = pc.get("h24") or 0.0

    # Liquidity score
    if liq >= 500_000:
        liq_score = 90
    elif liq >= 100_000:
        liq_score = 75
    elif liq >= 50_000:
        liq_score = 60
    elif liq >= 25_000:
        liq_score = 40
    elif liq >= 10_000:
        liq_score = 25
    else:
        liq_score = 10

    # Volume momentum
    if vol24 > 1_000_000 and h1 > 5:
        momentum = "strong"
    elif vol24 > 200_000 and h1 > 0:
        momentum = "moderate"
    elif vol24 > 30_000:
        momentum = "weak"
    else:
        momentum = "dying"

    # Holder risk (heuristic until real holder API is wired)
    flags = []
    if liq < 10_000:
        flags.append("extreme_low_liquidity")
    if liq < 25_000:
        flags.append("high_rug_risk")
    holder_score = max(5, min(90, liq_score - 10))

    # Action logic (conservative by design)
    action = "AVOID"
    confidence = 40

    if liq < 15_000 or momentum == "dying":
        action = "AVOID"
        confidence = 75
    elif liq >= 50_000 and momentum in ("strong", "moderate") and h1 > 3:
        action = "WATCH"
        confidence = 55
        if liq >= 100_000 and h24 > 20 and vol24 > 300_000:
            action = "BUY"
            confidence = 60
    else:
        action = "WATCH" if liq >= 25_000 else "AVOID"
        confidence = 45

    # Position sizing (very conservative)
    if action == "BUY":
        pct = 0.5 if liq > 200_000 else 0.25
        max_usd = min(150.0, liq * 0.01)  # never more than 1% of liquidity
    elif action == "WATCH":
        pct = 0.0
        max_usd = 0.0
    else:
        pct = 0.0
        max_usd = 0.0

    price = market.get("price_usd") or 0.0
    entry_low = price * 0.97 if price else None
    entry_high = price * 1.03 if price else None
    stop = price * 0.85 if price and action == "BUY" else None
    tps = []
    if price and action == "BUY":
        tps = [round(price * 1.5, 8), round(price * 2.5, 8)]

    rr = None
    if stop and price and tps:
        risk = price - stop
        reward = tps[0] - price
        if risk > 0:
            rr = round(reward / risk, 2)

    explanation_parts = [
        reports["technical"],
        reports["onchain_risk"],
        reports["sentiment"],
        reports["narrative"],
        reports["bull"],
        reports["bear"],
        reports["trader"],
        reports["risk"],
        f"\nFinal decision: {action} (confidence {confidence}%).",
        "This is a heuristic multi-agent simulation. Always do your own research and never risk money you cannot afford to lose.",
    ]

    base = market.get("base_token") or {}

    return Decision(
        action=action,
        confidence=confidence,
        liquidity_score=liq_score,
        volume_momentum=momentum,
        holder_risk=HolderRisk(
            score=holder_score,
            flags=flags,
            notes="Holder concentration not fully available without Helius/Birdeye. Verify on Solscan/RugCheck.",
        ),
        social_sentiment="unknown",
        technical_signals=[s.strip("- ") for s in reports["technical"].split("\n")[1:] if s.strip()],
        entry_zone={"low": entry_low, "high": entry_high},
        stop_loss=stop,
        take_profit=tps,
        position_sizing=PositionSizing(
            pct_of_portfolio=pct,
            max_usd=max_usd,
            rationale="Micro size only. Cap at ~1% of pool liquidity.",
        ),
        risk_reward=rr,
        explanation="\n\n".join(explanation_parts),
        token={
            "address": base.get("address"),
            "name": base.get("name"),
            "symbol": base.get("symbol"),
        },
        market={
            "price_usd": price,
            "liquidity_usd": liq,
            "volume_h24": vol24,
            "price_change_h1": h1,
            "price_change_h24": h24,
            "pair_address": market.get("pair_address"),
            "dex_id": market.get("dex_id"),
            "url": market.get("url"),
        },
        agent_reports=reports,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
