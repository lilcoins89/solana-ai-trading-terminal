"""
Solana AI Trading Terminal - Backend
Educational / research only. Paper trading default. Real trading OFF.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
    description=(
        "Multi-agent Solana token analysis inspired by TradingAgents. "
        "Paper trading only by default. Educational / research use."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Paper trading state (in-memory — resets on restart)
# ---------------------------------------------------------------------------
_paper_balance = 10_000.0
_paper_trades: list[dict] = []
_paper_positions: dict[str, dict] = {}  # token_address -> position


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.2.0",
        "mode": "paper",
        "real_trading": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/tokens/search")
async def token_search(q: str = Query(..., min_length=1), limit: int = 15):
    pairs = await search_pairs(q, limit=limit)
    return [normalize_pair(p) for p in pairs]


@app.get("/tokens/boosted")
async def tokens_boosted(limit: int = 20):
    return await boosted_tokens(limit=limit)


@app.get("/tokens/profiles")
async def tokens_profiles(limit: int = 25):
    return await latest_token_profiles(limit=limit)


async def _best_market(token_address: str) -> dict:
    pairs = await get_token_pairs(token_address)
    if not pairs:
        raise HTTPException(status_code=404, detail="No pairs found on DexScreener")
    sol = [p for p in pairs if p.get("chainId") == "solana"] or pairs
    best = max(sol, key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0))
    return normalize_pair(best)


@app.get("/analyze/{token_address}", response_model=Decision)
async def analyze_token(token_address: str):
    market = await _best_market(token_address)
    return run_analysis(market)


class BatchAnalyzeRequest(BaseModel):
    addresses: list[str] = Field(..., max_length=10)


@app.post("/analyze/batch")
async def analyze_batch(req: BatchAnalyzeRequest):
    """Analyze up to 10 tokens. Returns list of decisions (skips failures)."""
    results = []
    for addr in req.addresses[:10]:
        try:
            market = await _best_market(addr.strip())
            results.append(run_analysis(market).model_dump())
        except Exception as e:
            results.append({"token": {"address": addr}, "error": str(e)})
    return {"count": len(results), "results": results}


@app.get("/market/{token_address}")
async def market_snapshot(token_address: str):
    """Raw normalized market data without full agent pipeline."""
    return await _best_market(token_address)


# ---------------------------------------------------------------------------
# Paper trading
# ---------------------------------------------------------------------------

class PaperTradeRequest(BaseModel):
    token_address: str
    symbol: str
    side: str  # buy | sell
    usd_amount: float
    price: float
    note: Optional[str] = None


@app.get("/paper/summary")
async def paper_summary():
    positions = list(_paper_positions.values())
    unrealized = 0.0  # mark-to-market would need live prices; omitted in MVP
    return {
        "cash_usd": round(_paper_balance, 4),
        "open_positions": len(positions),
        "positions": positions,
        "trade_count": len(_paper_trades),
        "starting_balance": 10_000.0,
    }


@app.get("/paper/balance")
async def paper_balance():
    return {"balance_usd": _paper_balance, "trades": len(_paper_trades)}


@app.get("/paper/trades")
async def paper_trades(limit: int = 50):
    return _paper_trades[-limit:]


@app.get("/paper/positions")
async def paper_positions():
    return list(_paper_positions.values())


@app.post("/paper/trade")
async def paper_trade(req: PaperTradeRequest):
    global _paper_balance

    if req.side not in ("buy", "sell"):
        raise HTTPException(400, "side must be buy or sell")
    if req.usd_amount <= 0 or req.price <= 0:
        raise HTTPException(400, "usd_amount and price must be positive")

    qty = req.usd_amount / req.price
    addr = req.token_address

    if req.side == "buy":
        if req.usd_amount > _paper_balance:
            raise HTTPException(400, "Insufficient paper cash")
        _paper_balance -= req.usd_amount
        pos = _paper_positions.get(addr)
        if pos:
            new_qty = pos["qty"] + qty
            new_cost = pos["cost_usd"] + req.usd_amount
            pos["qty"] = new_qty
            pos["cost_usd"] = new_cost
            pos["avg_price"] = new_cost / new_qty if new_qty else 0
            pos["updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            _paper_positions[addr] = {
                "token_address": addr,
                "symbol": req.symbol,
                "qty": qty,
                "cost_usd": req.usd_amount,
                "avg_price": req.price,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
    else:
        pos = _paper_positions.get(addr)
        if not pos or pos["qty"] <= 0:
            raise HTTPException(400, "No open position to sell")
        sell_qty = min(qty, pos["qty"])
        proceeds = sell_qty * req.price
        _paper_balance += proceeds
        pos["qty"] -= sell_qty
        # reduce cost basis proportionally
        if pos["qty"] <= 1e-12:
            del _paper_positions[addr]
        else:
            ratio = pos["qty"] / (pos["qty"] + sell_qty)
            pos["cost_usd"] *= ratio
            pos["updated_at"] = datetime.now(timezone.utc).isoformat()
        qty = sell_qty

    trade = {
        "id": len(_paper_trades) + 1,
        "token_address": addr,
        "symbol": req.symbol,
        "side": req.side,
        "usd_amount": req.usd_amount if req.side == "buy" else proceeds,
        "price": req.price,
        "qty": qty,
        "balance_after": round(_paper_balance, 4),
        "note": req.note,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    _paper_trades.append(trade)
    return {"ok": True, "trade": trade, "balance_usd": _paper_balance, "positions": list(_paper_positions.values())}


@app.post("/paper/reset")
async def paper_reset():
    global _paper_balance, _paper_trades, _paper_positions
    _paper_balance = 10_000.0
    _paper_trades = []
    _paper_positions = {}
    return {"ok": True, "balance_usd": _paper_balance}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
