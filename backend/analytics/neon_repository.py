from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import asyncpg


class NeonRepository:
    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None
        self.backend = "neon-postgres"

    async def connect(self) -> None:
        if self.pool is None and os.getenv("DATABASE_URL"):
            self.pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=5)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def markets(self) -> list[dict[str, Any]]:
        if not self.pool: return []
        return [dict(r) for r in await self.pool.fetch("SELECT * FROM market_snapshots ORDER BY volume_24h DESC")]

    async def watchlist(self) -> list[dict[str, Any]]:
        if not self.pool: return []
        return [dict(r) for r in await self.pool.fetch("SELECT * FROM watchlist ORDER BY added_at DESC")]

    async def add_watch(self, item: dict[str, Any]) -> dict[str, Any]:
        assert self.pool
        await self.pool.execute("INSERT INTO watchlist (token_address,symbol,name,price,change_24h) VALUES ($1,$2,$3,$4,$5) ON CONFLICT (token_address) DO UPDATE SET symbol=EXCLUDED.symbol,name=EXCLUDED.name,price=EXCLUDED.price,change_24h=EXCLUDED.change_24h,added_at=NOW()", item["token_address"], item["symbol"], item.get("name", item["symbol"]), item.get("price", 0), item.get("change_24h", 0))
        return item

    async def remove_watch(self, address: str) -> None:
        assert self.pool
        await self.pool.execute("DELETE FROM watchlist WHERE token_address=$1", address)

    async def save_analysis(self, payload: dict[str, Any]) -> None:
        if not self.pool: return
        token = payload.get("token", {})
        await self.pool.execute("INSERT INTO analyses (token_address,symbol,action,confidence,payload) VALUES ($1,$2,$3,$4,$5::jsonb)", token.get("address", ""), token.get("symbol", ""), payload.get("action", ""), payload.get("confidence", 0), json.dumps(payload))

    async def analyses(self) -> list[dict[str, Any]]:
        if not self.pool: return []
        return [dict(r["payload"]) for r in await self.pool.fetch("SELECT payload FROM analyses ORDER BY created_at DESC LIMIT 20")]

    async def save_trade(self, trade: dict[str, Any]) -> None:
        if not self.pool: return
        await self.pool.execute("INSERT INTO paper_trades (token_address,symbol,side,usd_amount,price,qty,note,created_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)", trade["token_address"], trade["symbol"], trade["side"], trade["usd_amount"], trade["price"], trade["qty"], trade.get("note"), datetime.fromisoformat(trade["ts"]))

    async def trades(self) -> list[dict[str, Any]]:
        if not self.pool: return []
        return [dict(r) for r in await self.pool.fetch("SELECT * FROM paper_trades ORDER BY created_at DESC LIMIT 50")]

    async def history(self, symbol: str) -> list[dict[str, Any]]:
        if not self.pool:
            return []
        return [dict(r) for r in await self.pool.fetch("SELECT captured_at AS time, price FROM market_snapshots WHERE symbol=$1 ORDER BY captured_at ASC LIMIT 100", symbol.upper())]

repo = NeonRepository()
