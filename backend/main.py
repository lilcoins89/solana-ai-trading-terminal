"""Solana AI Trading Terminal — FastAPI backend. Paper mode. Educational only."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv

    load_dotenv("/vercel/share/.env.project")
    load_dotenv(Path(__file__).resolve().parent.parent / "frontend/.env.development.local")
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

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
from data.solana_tokens import solana_token_feed
from data.helius import (
    enrich_token,
    helius_configured,
    get_holder_concentration,
    get_token_authorities,
)
from data.rugcheck import enrich_rugcheck, get_report, get_summary
from data.solscan import enrich_solscan
from analysis.pipeline import run_analysis
from analysis.schemas import Decision
from analytics.neon_repository import repo

VERSION = "0.5.0"

app = FastAPI(
    title="Solana AI Trading Terminal",
    description=(
        "Multi-agent Solana analysis: DexScreener + Helius + RugCheck + Solscan. "
        "Paper trading only by default."
    ),
    version=VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_paper_balance = 10_000.0
_paper_trades: list[dict] = []
_paper_positions: dict[str, dict] = {}

@app.on_event("startup")
async def startup() -> None:
    await repo.connect()

@app.on_event("shutdown")
async def shutdown() -> None:
    await repo.close()


async def _enrich_all(mint: str, pair_address: str | None = None) -> tuple[dict, dict]:
    """Parallel Helius + RugCheck + Solscan."""
    helius, rug, sol = await asyncio.gather(
        enrich_token(mint),
        enrich_rugcheck(mint),
        enrich_solscan(mint, pair_address),
    )
    return helius, {"rugcheck": rug, "solscan": sol}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": VERSION,
        "mode": "paper",
        "real_trading": False,
        "helius_configured": helius_configured(),
        "rugcheck": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analytics": repo.backend,
    }


@app.get("/analytics/terminal")
async def terminal_snapshot():
    return {"markets": await repo.markets(), "watchlist": await repo.watchlist(), "analyses": await repo.analyses(), "trades": await repo.trades(), "analytics_backend": repo.backend}

@app.get("/analytics/markets/{symbol}/history")
async def market_history(symbol: str):
    return await repo.history(symbol)

@app.get("/analytics/watchlist")
async def analytics_watchlist():
    return await repo.watchlist()

@app.post("/analytics/watchlist")
async def add_watchlist(item: dict):
    return await repo.add_watch(item)

@app.delete("/analytics/watchlist/{address}")
async def delete_watchlist(address: str):
    await repo.remove_watch(address)
    return {"ok": True}

@app.get("/analytics/analyses")
async def analysis_history():
    return await repo.analyses()


@app.get("/helius/status")
async def helius_status():
    return {
        "configured": helius_configured(),
        "features": [
            "getTokenLargestAccounts",
            "getTokenSupply",
            "getAsset DAS (mint/freeze authority)",
        ],
        "hint": None
        if helius_configured()
        else "Set HELIUS_API_KEY — https://dashboard.helius.dev",
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
    return [p for p in await latest_token_profiles(limit=limit * 2) if p.get("chainId") == "solana"][:limit]

@app.get("/tokens/solana")
async def tokens_solana(limit: int = Query(12, ge=1, le=30)):
    return await solana_token_feed(limit)


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
    mint = (market.get("base_token") or {}).get("address") or token_address
    helius, cross = await _enrich_all(mint, market.get("pair_address"))
    result = run_analysis(market, helius, cross)
    await repo.save_analysis(result.model_dump())
    return result


class BatchAnalyzeRequest(BaseModel):
    addresses: list[str] = Field(..., max_length=10)


@app.post("/analyze/batch")
async def analyze_batch(req: BatchAnalyzeRequest):
    results = []
    for addr in req.addresses[:10]:
        try:
            market = await _best_market(addr.strip())
            mint = (market.get("base_token") or {}).get("address") or addr.strip()
            helius, cross = await _enrich_all(mint, market.get("pair_address"))
            results.append(run_analysis(market, helius, cross).model_dump())
        except Exception as e:
            results.append({"token": {"address": addr}, "error": str(e)})
    return {"count": len(results), "results": results}


@app.get("/market/{token_address}")
async def market_snapshot(token_address: str):
    return await _best_market(token_address)


@app.get("/crosscheck/{token_address}")
async def crosscheck(token_address: str):
    market = None
    try:
        market = await _best_market(token_address)
    except Exception:
        pass
    mint = (
        (market.get("base_token") or {}).get("address") if market else None
    ) or token_address
    _, cross = await _enrich_all(mint, (market or {}).get("pair_address"))
    return cross


@app.get("/rugcheck/{token_address}")
async def rugcheck_report(token_address: str, summary: bool = False):
    data = await (get_summary(token_address) if summary else get_report(token_address))
    if not data:
        raise HTTPException(404, "RugCheck report not found")
    return data


@app.get("/helius/holders/{token_address}")
async def helius_holders(token_address: str):
    if not helius_configured():
        raise HTTPException(503, "HELIUS_API_KEY not configured")
    return await get_holder_concentration(token_address)


@app.get("/helius/authorities/{token_address}")
async def helius_authorities(token_address: str):
    if not helius_configured():
        raise HTTPException(503, "HELIUS_API_KEY not configured")
    return await get_token_authorities(token_address)


class PaperTradeRequest(BaseModel):
    token_address: str
    symbol: str
    side: str
    usd_amount: float
    price: float
    note: Optional[str] = None


@app.get("/paper/summary")
async def paper_summary():
    return {
        "cash_usd": round(_paper_balance, 4),
        "open_positions": len(_paper_positions),
        "positions": list(_paper_positions.values()),
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
    proceeds = req.usd_amount

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
    await repo.save_trade(trade)
    return {
        "ok": True,
        "trade": trade,
        "balance_usd": _paper_balance,
        "positions": list(_paper_positions.values()),
    }


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
