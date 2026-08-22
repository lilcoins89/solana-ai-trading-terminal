from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(__import__('os').environ.get('ANALYTICS_DB_PATH', str(ROOT / 'data' / 'terminal.duckdb')))

class AnalyticsRepository:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.backend = "duckdb"
        try:
            import duckdb
            self.db = duckdb.connect(str(path))
        except ImportError:
            self.backend = "sqlite-fallback"
            self.db = sqlite3.connect(str(path.with_suffix('.sqlite3')), check_same_thread=False)
        self._init()

    def _init(self):
        self.db.execute("""CREATE TABLE IF NOT EXISTS market_snapshots (id INTEGER PRIMARY KEY, symbol VARCHAR, name VARCHAR, price DOUBLE, change_24h DOUBLE, volume_24h DOUBLE, liquidity DOUBLE, captured_at TIMESTAMP)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS analyses (id INTEGER PRIMARY KEY, token_address VARCHAR, symbol VARCHAR, action VARCHAR, confidence DOUBLE, payload VARCHAR, created_at TIMESTAMP)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS watchlist (token_address VARCHAR PRIMARY KEY, symbol VARCHAR, name VARCHAR, price DOUBLE, change_24h DOUBLE, added_at TIMESTAMP)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS paper_trades (id INTEGER PRIMARY KEY, token_address VARCHAR, symbol VARCHAR, side VARCHAR, usd_amount DOUBLE, price DOUBLE, qty DOUBLE, note VARCHAR, created_at TIMESTAMP)""")
        if not self.db.execute("SELECT COUNT(*) FROM market_snapshots").fetchone()[0]:
            now = datetime.now(timezone.utc).isoformat()
            rows = [(1,'SOL','Solana',178.42,4.82,2840000000,8120000000,now),(2,'JUP','Jupiter',1.12,-2.14,182000000,412000000,now),(3,'BONK','Bonk',0.000031,8.67,94000000,210000000,now),(4,'WIF','dogwifhat',2.84,1.34,211000000,530000000,now),(5,'PYTH','Pyth Network',0.39,-0.78,68000000,124000000,now)]
            self.db.executemany("INSERT INTO market_snapshots VALUES (?,?,?,?,?,?,?,?)", rows)

    def markets(self):
        return [dict(zip(['id','symbol','name','price','change_24h','volume_24h','liquidity','captured_at'], r)) for r in self.db.execute("SELECT * FROM market_snapshots ORDER BY volume_24h DESC").fetchall()]
    def history(self, symbol: str):
        base = next((m for m in self.markets() if m['symbol'] == symbol.upper()), self.markets()[0])
        price = float(base['price'])
        return [{'time': f"-{(11-i)*2}h", 'price': round(price*(1 + ((i-5)*0.008) + ((i%3-1)*0.004)), 8)} for i in range(12)]
    def watchlist(self):
        return [dict(zip(['token_address','symbol','name','price','change_24h','added_at'], r)) for r in self.db.execute("SELECT * FROM watchlist ORDER BY added_at DESC").fetchall()]
    def add_watch(self, item: dict[str, Any]):
        self.db.execute("INSERT OR REPLACE INTO watchlist VALUES (?,?,?,?,?,?)", (item['token_address'],item['symbol'],item.get('name',item['symbol']),item.get('price',0),item.get('change_24h',0),datetime.now(timezone.utc).isoformat()))
        return item
    def remove_watch(self, address: str):
        self.db.execute("DELETE FROM watchlist WHERE token_address = ?", (address,))
    def save_analysis(self, payload: dict[str, Any]):
        self.db.execute("INSERT INTO analyses VALUES (?,?,?,?,?,?,?)", (None,payload.get('token',{}).get('address',''),payload.get('token',{}).get('symbol',''),payload.get('action',''),payload.get('confidence',0),json.dumps(payload),datetime.now(timezone.utc).isoformat()))
    def analyses(self):
        return [json.loads(r[0]) for r in self.db.execute("SELECT payload FROM analyses ORDER BY created_at DESC LIMIT 20").fetchall()]
    def save_trade(self, t: dict[str, Any]):
        self.db.execute("INSERT INTO paper_trades VALUES (?,?,?,?,?,?,?,?,?)", (t['id'],t['token_address'],t['symbol'],t['side'],t['usd_amount'],t['price'],t['qty'],t.get('note'),t['ts']))
    def trades(self):
        rows = self.db.execute("SELECT * FROM paper_trades ORDER BY created_at DESC LIMIT 50").fetchall()
        return [dict(zip(['id','token_address','symbol','side','usd_amount','price','qty','note','created_at'],r)) for r in rows]
    def reset(self):
        for table in ('analyses','paper_trades','watchlist'): self.db.execute(f'DELETE FROM {table}')

repo = AnalyticsRepository()
