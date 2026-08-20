from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class HolderRisk(BaseModel):
    score: int = Field(ge=0, le=100, description="Higher = safer")
    top1_pct: Optional[float] = None
    top5_pct: Optional[float] = None
    top10_pct: Optional[float] = None
    top20_pct: Optional[float] = None
    mint_authority_renounced: Optional[bool] = None
    freeze_authority_renounced: Optional[bool] = None
    helius_configured: bool = False
    flags: list[str] = []
    notes: str = ""
    details: dict[str, Any] = {}


class PositionSizing(BaseModel):
    pct_of_portfolio: float
    max_usd: float
    rationale: str = ""


class Decision(BaseModel):
    action: Literal["BUY", "WATCH", "AVOID"]
    confidence: int = Field(ge=0, le=100)
    liquidity_score: int = Field(ge=0, le=100)
    volume_momentum: Literal["strong", "moderate", "weak", "dying"]
    holder_risk: HolderRisk
    social_sentiment: Literal["bullish", "neutral", "bearish", "unknown"]
    technical_signals: list[str]
    entry_zone: dict[str, Optional[float]]
    stop_loss: Optional[float]
    take_profit: list[float]
    position_sizing: PositionSizing
    risk_reward: Optional[float]
    explanation: str
    token: dict
    market: dict
    agent_reports: dict[str, str] = {}
    timestamp: str
