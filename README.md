# Solana AI Trading Terminal

> **Educational only — not financial advice.** Most Solana memecoins go to zero. Paper mode is the default. Real trading is off.

Multi-agent Solana research terminal: **DexScreener** discovery + **Helius** holders/authorities + **RugCheck** LP/sniper risks + **Solscan** links.

**Repo:** https://github.com/lilcoins89/solana-ai-trading-terminal  
**Version:** 0.4.1

---

## Quick start

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Optional but recommended:
#   HELIUS_API_KEY=...     https://dashboard.helius.dev
#   RUGCHECK_API_KEY=...   optional rate-limit boost
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 · API docs http://localhost:8000/docs

---

## What each layer does

| Source | Role |
|--------|------|
| DexScreener | Search, price, liquidity, volume, tx flow |
| Helius | Top holder %, mint/freeze authority |
| RugCheck | LP locked %, risk list, sniper/insider keywords |
| Solscan | Explorer links (holders / transfers) |
| Agents | Technical → Risk → Sentiment → Narrative → Bull/Bear → Trader → Risk Manager |

**Decision:** `BUY` / `WATCH` / `AVOID` + confidence, levels, position size, full explanation, `cross_check` block.

Hard avoids include: extreme concentration, unlocked LP, active mint + thin liq, sniper signals + weak lock.

---

## API (highlights)

| Method | Path |
|--------|------|
| GET | `/health` |
| GET | `/analyze/{mint}` |
| POST | `/analyze/batch` |
| GET | `/crosscheck/{mint}` |
| GET | `/rugcheck/{mint}` |
| GET | `/helius/holders/{mint}` |
| GET | `/tokens/search?q=` |
| GET/POST | `/paper/*` |

```bash
curl -s http://localhost:8000/analyze/<MINT> | jq '{action, confidence, cross_check}'
```

---

## Project layout

```
backend/
  main.py              # FastAPI 0.4.1 — parallel enrichment
  agents/roles.py
  analysis/pipeline.py + schemas.py
  data/dexscreener.py | helius.py | rugcheck.py | solscan.py
frontend/
  app/page.tsx         # Terminal UI
  app/layout.tsx       # Wallet adapter
```

---

## Safety

- Paper ledger is in-memory (resets on restart).
- Always verify RugCheck + Solscan yourself before risking capital.
- Never enable real trading without a full audit.

## License

MIT
