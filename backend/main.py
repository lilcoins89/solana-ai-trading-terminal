"""
Solana AI Trading Terminal - Backend
Educational / research only. Paper trading default.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as module
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data.dexscreener import (
    search_pairs,
    get_token_pairs,
    normalize_pair,
    boosted_tokens,
    latest_token_profiles,
)
from analysis.pipeline import run_analysis
from analysis.schemas import Decision

app = FastAPI(
    title="Solana AI Trading Terminal",
    description="Multi-agent analysis for Solana tokens. Educational only.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "paper", "real_trading": False}


@app.get("/tokens/search")
async def token_search(q: str = Query(..., min_length=1), limit: int = 15):
    pairs = await search_pairs(q, limit=limit)
    return [normalize_pair(p) for p in pairs]


@app.get("/tokens/boosted")
async def tokens_boosted(limit: int = 15):
    data = await boosted_tokens(limit=limit)
    return data


@app.get("/tokens/profiles")
async def tokens_profiles(limit: int = 20):
    data = await latest_token_profiles(limit=limit)
    return data


@app.get("/analyze/{token_address}", response_model=Decision)
async def analyze_token(token_address: str):
    pairs = await get_token_pairs(token_address)
    if not pairs:
        raise HTTPException(status_code=404, detail="No pairs found for this token on DexScreener")

    # Prefer highest liquidity Solana pair
    sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
    if not sol_pairs:
        sol_pairs = pairs

    best = max(sol_pairs, key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0))
    market = normalize_pair(best)
    decision = run_analysis(market)
    return decision


class PaperTradeRequest(BaseModel):
    token_address: str
    symbol: str
    side: str  # buy | sell
    usd_amount: float
    price: float


# Simple in-memory paper ledger (resets on restart)
_paper_trades: list[dict] = []
_paper_balance = 10_000.0


@app.get("/paper/balance")
async def paper_balance():
    return {"balance_usd": _paper_balance, "trades": len(_paper_trades)}


@app.get("/paper/trades")
async def paper_trades():
    return _paper_trades[-50:]


@app.post("/paper/trade")
async def paper_trade(req: PaperTradeRequest):
    global _paper_balance
    if req.side not in ("buy", "sell"):
        raise HTTPException(400, "side must be buy or sell")
    if req.usd_amount <= 0:
        raise HTTPException(400, "usd_amount must be positive")

    if req.side == "buy":
        if req.usd_amount > _paper_balance:
            raise HTTPException(400, "Insufficient paper balance")
        _paper_balance -= req.usd_amount
        qty = req.usd_amount / req.price if req.price > 0 else 0
    else:
        # simplified: we don't track positions tightly in this MVP
        qty = req.usd_amount / req.price if req.price > 0 else 0
        _paper_balance += req.usd_amount

    trade = {
        "token_address": req.token_address,
        "symbol": req.symbol,
        "side": req.side,
        "usd_amount": req.usd_amount,
        "price": req.price,
        "qty": qty,
        "balance_after": _paper_balance,
    }
    _paper_trades.append(trade)
    return {"ok": True, "trade": trade, "balance_usd": _paper_balance}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
