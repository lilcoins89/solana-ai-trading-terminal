"""Orchestrates the multi-agent analysis pipeline and produces a Decision."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from agents.roles import (
    technical_analyst,
    onchain_risk_analyst,
    sentiment_analyst,
    narrative_analyst,
    bull_researcher,
    bear_researcher,
    trader_agent,
    risk_manager,
    _txn_pressure,
    _age_hours,
)
from analysis.schemas import Decision, HolderRisk, PositionSizing


def _clamp(x: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, round(x))))


def run_analysis(market: dict[str, Any], helius: dict[str, Any] | None = None) -> Decision:
    """Run the full agent pipeline on a normalized market snapshot + optional Helius data."""

    helius = helius or {"configured": False}
    holders = helius.get("holders") or {}
    authorities = helius.get("authorities") or {}

    reports = {
        "technical": technical_analyst(market),
        "onchain_risk": onchain_risk_analyst(market, helius),
        "sentiment": sentiment_analyst(market),
        "narrative": narrative_analyst(market),
    }
    reports["bull"] = bull_researcher(reports, market)
    reports["bear"] = bear_researcher(reports, market, helius)
    reports["trader"] = trader_agent(reports, market)
    reports["risk"] = risk_manager(reports, market, helius)

    liq = float(market.get("liquidity_usd") or 0.0)
    vol = market.get("volume") or {}
    vol24 = float(vol.get("h24") or 0.0)
    vol1 = float(vol.get("h1") or 0.0)
    pc = market.get("price_change") or {}
    h1 = float(pc.get("h1") or 0.0)
    h6 = float(pc.get("h6") or 0.0)
    h24 = float(pc.get("h24") or 0.0)
    m5 = float(pc.get("m5") or 0.0)
    price = float(market.get("price_usd") or 0.0)
    fdv = float(market.get("fdv") or market.get("market_cap") or 0.0)
    age_h = _age_hours(market.get("pair_created_at"))
    buy_r1, buy_r24, tx_h1 = _txn_pressure(market.get("txns") or {})
    boosts = int((market.get("boosts") or {}).get("active") or 0)

    top1 = holders.get("top1_pct")
    top5 = holders.get("top5_pct")
    top10 = holders.get("top10_pct")
    top20 = holders.get("top20_pct")
    mint_ren = authorities.get("mint_authority_renounced")
    freeze_ren = authorities.get("freeze_authority_renounced")

    # ---------- Liquidity score ----------
    if liq >= 1_000_000:
        liq_score = 95
    elif liq >= 300_000:
        liq_score = 85
    elif liq >= 100_000:
        liq_score = 72
    elif liq >= 50_000:
        liq_score = 58
    elif liq >= 25_000:
        liq_score = 42
    elif liq >= 10_000:
        liq_score = 28
    elif liq >= 5_000:
        liq_score = 15
    else:
        liq_score = 5

    if fdv > 0 and liq > 0:
        ratio = liq / fdv
        if ratio < 0.015:
            liq_score = max(5, liq_score - 20)
        elif ratio < 0.03:
            liq_score = max(5, liq_score - 10)

    # ---------- Volume momentum ----------
    if vol24 > 1_500_000 and h1 > 5 and buy_r1 > 0.52:
        momentum: Literal["strong", "moderate", "weak", "dying"] = "strong"
    elif vol24 > 300_000 and (h1 > 0 or buy_r1 > 0.55):
        momentum = "moderate"
    elif vol24 > 40_000:
        momentum = "weak"
    else:
        momentum = "dying"

    # ---------- Holder / structural risk (Helius-aware) ----------
    flags: list[str] = []
    holder_score = 55.0

    if liq < 5_000:
        flags.append("extreme_low_liquidity")
        holder_score -= 35
    elif liq < 15_000:
        flags.append("high_rug_risk")
        holder_score -= 25
    elif liq < 40_000:
        flags.append("elevated_exit_risk")
        holder_score -= 12

    if age_h is not None:
        if age_h < 1:
            flags.append("ultra_new_pair")
            holder_score -= 20
        elif age_h < 6:
            flags.append("young_pair")
            holder_score -= 10
        elif age_h > 72:
            holder_score += 8

    if boosts > 0:
        flags.append("paid_boost")
        holder_score -= 5

    if h24 > 150:
        flags.append("extended_parabolic")
        holder_score -= 8

    # Real concentration from Helius
    if top1 is not None:
        if top1 >= 40:
            flags.append("top1_extreme")
            holder_score -= 35
        elif top1 >= 20:
            flags.append("top1_high")
            holder_score -= 18
        elif top1 >= 12:
            flags.append("top1_elevated")
            holder_score -= 8
        else:
            holder_score += 5

    if top10 is not None:
        if top10 >= 75:
            flags.append("top10_extreme")
            holder_score -= 30
        elif top10 >= 55:
            flags.append("top10_high")
            holder_score -= 15
        elif top10 >= 40:
            flags.append("top10_elevated")
            holder_score -= 6
        else:
            holder_score += 6

    if mint_ren is True:
        holder_score += 8
    elif mint_ren is False:
        flags.append("mint_authority_active")
        holder_score -= 15

    if freeze_ren is True:
        holder_score += 4
    elif freeze_ren is False:
        flags.append("freeze_authority_active")
        holder_score -= 8

    if not helius.get("configured"):
        flags.append("helius_not_configured")

    holder_score = _clamp(holder_score, 5, 95)

    # ---------- Social sentiment proxy ----------
    social: Literal["bullish", "neutral", "bearish", "unknown"] = "unknown"
    if h1 > 8 and buy_r1 >= 0.58 and tx_h1 >= 25:
        social = "bullish"
    elif h1 < -8 and buy_r1 <= 0.42 and tx_h1 >= 25:
        social = "bearish"
    elif tx_h1 >= 15:
        social = "neutral"

    # ---------- Composite edge ----------
    edge = 40.0
    edge += min(20, h1 * 0.8) if h1 > 0 else max(-20, h1 * 0.6)
    edge += 12 if momentum == "strong" else 6 if momentum == "moderate" else -5 if momentum == "dying" else 0
    edge += (buy_r1 - 0.5) * 40
    edge += (liq_score - 50) * 0.25
    edge += (holder_score - 50) * 0.35  # stronger weight when Helius data present
    if age_h is not None and age_h < 2:
        edge -= 12
    if h24 > 120:
        edge -= 10
    if m5 > 15:
        edge -= 6
    edge = _clamp(edge, 0, 100)

    # ---------- Action ----------
    action: Literal["BUY", "WATCH", "AVOID"] = "AVOID"
    confidence = 50

    hard_avoid = (
        liq < 12_000
        or momentum == "dying"
        or (age_h is not None and age_h < 0.75 and liq < 60_000)
        or vol24 < 12_000
        or "extreme_low_liquidity" in flags
        or "top1_extreme" in flags
        or "top10_extreme" in flags
        or (mint_ren is False and liq < 100_000)
    )

    if hard_avoid:
        action = "AVOID"
        confidence = _clamp(70 + (15 if liq < 8_000 else 0))
    elif (
        edge >= 68
        and liq >= 80_000
        and momentum in ("strong", "moderate")
        and holder_score >= 50
        and (top10 is None or top10 < 55)
        and mint_ren is not False
    ):
        action = "BUY"
        confidence = _clamp(55 + (edge - 68) * 0.7)
    elif edge >= 52 and liq >= 30_000:
        action = "WATCH"
        confidence = _clamp(50 + (edge - 50) * 0.4)
    elif liq >= 25_000 and momentum != "dying":
        action = "WATCH"
        confidence = 48
    else:
        action = "AVOID"
        confidence = _clamp(55 + (50 - edge) * 0.3)

    if "HARD AVOID" in reports["risk"] or "REJECT" in reports["risk"]:
        action = "AVOID"
        confidence = max(confidence, 72)

    # ---------- Sizing ----------
    if action == "BUY":
        pct = 0.75 if liq > 250_000 and holder_score > 55 else 0.35
        max_usd = min(200.0, liq * 0.008)
        if holder_score < 50:
            max_usd = min(max_usd, 75.0)
            pct = min(pct, 0.25)
    else:
        pct = 0.0
        max_usd = 0.0

    entry_low = round(price * 0.96, 10) if price else None
    entry_high = round(price * 1.02, 10) if price else None

    if action == "BUY" and price:
        stop_pct = 0.12 if (age_h or 99) < 12 or liq < 100_000 else 0.15
        stop = round(price * (1 - stop_pct), 10)
        tps = [round(price * 1.4, 10), round(price * 2.2, 10), round(price * 3.5, 10)]
    else:
        stop = None
        tps = []

    rr = None
    if stop and price and tps:
        risk = price - stop
        reward = tps[0] - price
        if risk > 0:
            rr = round(reward / risk, 2)

    tech_lines = [
        ln.strip().lstrip("- ").strip()
        for ln in reports["technical"].split("\n")[1:]
        if ln.strip()
    ]

    helius_note = (
        "Helius enrichment active (holders + authorities)."
        if helius.get("configured")
        else "Helius not configured — add HELIUS_API_KEY for holder concentration & authorities."
    )

    explanation = "\n\n".join(
        [
            reports["technical"],
            reports["onchain_risk"],
            reports["sentiment"],
            reports["narrative"],
            reports["bull"],
            reports["bear"],
            reports["trader"],
            reports["risk"],
            f"Composite edge score: {edge}/100",
            helius_note,
            f"Final decision: {action} (confidence {confidence}%).",
            "Heuristic multi-agent system for research only. Not financial advice. DYOR.",
        ]
    )

    base = market.get("base_token") or {}

    return Decision(
        action=action,
        confidence=confidence,
        liquidity_score=liq_score,
        volume_momentum=momentum,
        holder_risk=HolderRisk(
            score=holder_score,
            top1_pct=top1,
            top5_pct=top5,
            top10_pct=top10,
            top20_pct=top20,
            mint_authority_renounced=mint_ren,
            freeze_authority_renounced=freeze_ren,
            helius_configured=bool(helius.get("configured")),
            flags=flags,
            notes=(
                "Holder concentration from Helius getTokenLargestAccounts; "
                "authorities from DAS getAsset. Always cross-check RugCheck/Solscan."
                if helius.get("configured")
                else "Structural proxies only. Set HELIUS_API_KEY for real holder data."
            ),
            details={
                "largest_accounts": (holders.get("largest_accounts") or [])[:10],
                "mint_authority": authorities.get("mint_authority"),
                "freeze_authority": authorities.get("freeze_authority"),
                "supply_ui": holders.get("supply_ui"),
            },
        ),
        social_sentiment=social,
        technical_signals=tech_lines,
        entry_zone={"low": entry_low, "high": entry_high},
        stop_loss=stop,
        take_profit=tps,
        position_sizing=PositionSizing(
            pct_of_portfolio=pct,
            max_usd=round(max_usd, 2),
            rationale=(
                "Micro-size only. Cap by % of portfolio and % of pool liquidity. "
                "Never size for a home-run on new Solana pairs."
            ),
        ),
        risk_reward=rr,
        explanation=explanation,
        token={
            "address": base.get("address"),
            "name": base.get("name"),
            "symbol": base.get("symbol"),
        },
        market={
            "price_usd": price,
            "liquidity_usd": liq,
            "volume_h1": vol1,
            "volume_h24": vol24,
            "price_change_m5": m5,
            "price_change_h1": h1,
            "price_change_h6": h6,
            "price_change_h24": h24,
            "buy_ratio_h1": round(buy_r1, 3),
            "tx_h1": tx_h1,
            "fdv": fdv,
            "age_hours": round(age_h, 2) if age_h is not None else None,
            "pair_address": market.get("pair_address"),
            "dex_id": market.get("dex_id"),
            "url": market.get("url"),
        },
        agent_reports=reports,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
