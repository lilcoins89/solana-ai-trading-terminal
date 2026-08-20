# Solana AI Trading Terminal

> **Educational / Research Project Only — Not Financial Advice**  
> Solana memecoins are extremely high risk. Most go to zero. Never risk money you cannot afford to lose. **Real trading is disabled by default.**

A layered, multi-agent AI terminal for Solana token discovery and decision support, inspired by [TradingAgents](https://github.com/TauricResearch/TradingAgents).

**Repo:** https://github.com/lilcoins89/solana-ai-trading-terminal  
**Version:** 0.3.0

---

## Why this exists

Retail Solana trading is noisy: hundreds of new pairs, rugs, paid boosts, and thin liquidity. This project gives you a **structured multi-agent reasoning layer** on top of live DexScreener + **Helius** data so you can:

1. Discover tokens
2. Run a full agent debate-style analysis (including real holder concentration)
3. Get a clear **BUY / WATCH / AVOID** with confidence, risk metrics, and levels
4. Paper-trade the ideas without risking capital

It deliberately keeps **wallet connection**, **intelligence**, and **execution** in separate layers.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR WEB APP (Next.js)                  │
│         Solana Wallet Adapter  ·  Search  ·  Analysis UI    │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
 Token Discovery      Market Data           Helius
  (DexScreener)    price·liq·volume    holders·authorities
        │                   │                   │
        └───────────────────┴───────────────────┘
                            ▼
                 AI MULTI-AGENT ENGINE
         Technical · On-chain Risk · Sentiment
         Narrative · Bull/Bear · Trader · Risk Mgr
                            ▼
                   Structured Decision
                            │
                 Paper Trading (Real OFF)
```

---

## Helius integration (v0.3)

Get a free API key: [https://dashboard.helius.dev](https://dashboard.helius.dev)

```bash
cd backend
cp .env.example .env
# Edit .env:
HELIUS_API_KEY=your_key_here
```

Restart the backend. Check:

```bash
curl -s http://localhost:8000/helius/status
curl -s http://localhost:8000/health | jq .helius_configured
```

### What Helius powers

| Method | Use |
|--------|-----|
| `getTokenLargestAccounts` | Top holder % (top1 / top5 / top10 / top20) |
| `getTokenSupply` | Supply for concentration math |
| `getAsset` (DAS) | Mint authority & freeze authority (renounced or active) |

These feed the **On-chain Risk Analyst**, **Bear Researcher**, **Risk Manager**, and the holder_risk block on every Decision.

Without a key the app still runs; holder fields stay empty and agents note that Helius is not configured.

### Hard risk vetoes (when Helius data is present)

- Top-10 holders ≥ 75% → HARD AVOID
- Single wallet ≥ 40% → HARD AVOID
- Active mint authority + modest liquidity → AVOID / REJECT

---

## Features (v0.3)

### Intelligence
- **7 agent roles** (TradingAgents-style) for Solana memecoins
- **Helius** holder concentration + mint/freeze authority
- Composite edge score (momentum, flow, liquidity, age, concentration)
- Conservative BUY / WATCH / AVOID policy

### Decision card
| Field | Description |
|--------|-------------|
| Action | 🟢 BUY / 🟡 WATCH / 🔴 AVOID |
| Confidence | 0–100 |
| Liquidity score | 0–100 |
| Volume momentum | strong / moderate / weak / dying |
| Holder risk | score, top1/5/10/20 %, mint/freeze renounced, flags |
| Social sentiment | bullish / neutral / bearish / unknown |
| Technical signals | list |
| Entry / SL / TP | levels |
| Position sizing | % portfolio + max USD (capped vs pool) |
| Risk/Reward | vs first TP |
| Explanation | full multi-agent report |

---

## Quick Start

### Prerequisites
- **Node.js 20+**
- **Python 3.11+**
- **Helius API key** (recommended)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add HELIUS_API_KEY=...
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs  
Health: http://localhost:8000/health

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Status, version, `helius_configured` |
| GET | `/helius/status` | Helius feature list |
| GET | `/helius/holders/{mint}` | Raw concentration |
| GET | `/helius/authorities/{mint}` | Mint/freeze authority |
| GET | `/tokens/search?q=&limit=` | Search Solana pairs |
| GET | `/tokens/boosted` | Top boosted tokens |
| GET | `/tokens/profiles` | Latest profiles |
| GET | `/market/{mint}` | Normalized market snapshot |
| GET | `/analyze/{mint}` | Full multi-agent Decision (+ Helius) |
| POST | `/analyze/batch` | Up to 10 mints |
| GET | `/paper/summary` | Cash + positions |
| GET | `/paper/balance` | Cash |
| GET | `/paper/positions` | Open positions |
| GET | `/paper/trades` | Recent trades |
| POST | `/paper/trade` | Paper buy/sell |
| POST | `/paper/reset` | Reset to $10k |

```bash
curl -s http://localhost:8000/analyze/<MINT> | jq '{action, confidence, holder_risk}'
```

---

## Project structure

```
backend/
  main.py                 # FastAPI v0.3
  agents/roles.py         # Multi-agent roles (Helius-aware)
  analysis/pipeline.py    # Scoring + decision engine
  analysis/schemas.py     # Decision / HolderRisk models
  data/dexscreener.py     # DexScreener client
  data/helius.py          # Helius RPC/DAS client
  .env.example
frontend/
  app/page.tsx            # Terminal UI
  app/layout.tsx          # Wallet providers
```

---

## Safety & limitations

- **Not financial advice.** Research tool only.
- Helius top accounts are the largest **token accounts** (not always unique wallets after ATA aggregation nuances).
- LP lock % and sniper/bundle detection are **not** fully covered — still use RugCheck / Solscan.
- Social sentiment is a price/flow proxy, not live X/TG scraping.
- Paper ledger is in-memory (resets on restart).
- Never enable real trading until you fully audit the execution path.

---

## Roadmap

- [x] Helius holder concentration + mint/freeze authority
- [ ] Optional LLM layer on top of structured scores
- [ ] RugCheck / Birdeye cross-checks
- [ ] Live X sentiment module
- [ ] Persistent paper DB
- [ ] Watchlist + alerts
- [ ] Jupiter quote (user-signed only)
- [ ] Full LangGraph TradingAgents port
- [ ] Docker Compose

---

## Disclaimer

This software is provided for educational and research purposes only, **as-is**, without warranty of any kind. Cryptocurrency trading involves substantial risk of loss. Authors and contributors are not responsible for any financial losses or damages arising from use of this software.

## License

MIT
