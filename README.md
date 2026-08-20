# Solana AI Trading Terminal

> **Educational / Research Project Only — Not Financial Advice**  
> Solana memecoins are extremely high risk. Most go to zero. Never risk money you cannot afford to lose. **Real trading is disabled by default.**

A layered, multi-agent AI terminal for Solana token discovery and decision support, inspired by [TradingAgents](https://github.com/TauricResearch/TradingAgents).

**Repo:** https://github.com/lilcoins89/solana-ai-trading-terminal  
**Version:** 0.2.0

---

## Why this exists

Retail Solana trading is noisy: hundreds of new pairs, rugs, paid boosts, and thin liquidity. This project gives you a **structured multi-agent reasoning layer** on top of live DexScreener data so you can:

1. Discover tokens
2. Run a full agent debate-style analysis
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
              ┌─────────────┴─────────────┐
              ▼                           ▼
     Token Discovery              Market Data Layer
      (DexScreener)            prices · liq · volume · txns
              │                           │
              └─────────────┬─────────────┘
                            ▼
                 AI MULTI-AGENT ENGINE
         ┌──────────┬─────────┬──────────┐
         │Technical │ On-chain│ Sentiment│
         │ Analyst  │  Risk   │ Analyst  │
         └────┬─────┴────┬────┴────┬─────┘
              │          │         │
         Narrative   Bull / Bear Researchers
              │          │
              └────┬─────┘
                   ▼
              Trader Agent
                   ▼
             Risk Manager  ──►  Structured Decision
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
    Paper Trading      (Real exec OFF)
```

---

## Features (v0.2)

### Intelligence
- **7 agent roles** adapted for Solana memecoins (TradingAgents-style):
  - Technical Analyst (multi-TF momentum, volume acceleration, buy/sell pressure)
  - On-chain / Holder Risk Analyst (liquidity, liq/FDV, pair age, boost flags)
  - Sentiment Analyst (socials, boosts, flow-based proxy sentiment)
  - Narrative Analyst (theme heuristics + labels)
  - Bull & Bear Researchers (structured debate)
  - Trader Agent
  - Risk Manager (hard vetoes)
- **Composite edge score** combining momentum, flow, liquidity, age, and structure
- Conservative decision policy (defaults to AVOID / WATCH)

### Decision card (every analysis)
| Field | Description |
|--------|-------------|
| Action | 🟢 BUY / 🟡 WATCH / 🔴 AVOID |
| Confidence | 0–100 |
| Liquidity score | 0–100 |
| Volume momentum | strong / moderate / weak / dying |
| Holder risk | score + flags + notes |
| Social sentiment | bullish / neutral / bearish / unknown |
| Technical signals | list |
| Entry zone | low–high |
| Stop-loss | suggested invalidation |
| Take-profit | multi-level targets |
| Position sizing | % portfolio + max USD (capped vs pool) |
| Risk/Reward | vs first TP |
| Full explanation | concatenated agent reports |

### Data & API
- DexScreener search, token pairs, boosted tokens, latest profiles
- `GET /analyze/{mint}` — full multi-agent decision
- `POST /analyze/batch` — up to 10 mints
- `GET /market/{mint}` — raw normalized snapshot
- Paper ledger with **cash, positions, trade history, reset**

### Frontend
- Next.js + Solana Wallet Adapter (Phantom, Solflare)
- Search → select → full analysis panel
- Dark terminal UI

### Safety
- Paper mode only
- Real trading flag hard-off
- Position size capped as % of pool liquidity
- Explicit educational disclaimer

---

## Quick Start

### Prerequisites
- **Node.js 20+**
- **Python 3.11+**

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # optional LLM keys for future upgrades
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

Optional: set `NEXT_PUBLIC_API_URL=http://localhost:8000` if the API is elsewhere.

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Status + version |
| GET | `/tokens/search?q=&limit=` | Search Solana pairs |
| GET | `/tokens/boosted` | Top boosted tokens |
| GET | `/tokens/profiles` | Latest token profiles |
| GET | `/market/{mint}` | Normalized market snapshot |
| GET | `/analyze/{mint}` | Full multi-agent Decision |
| POST | `/analyze/batch` | Body: `{ "addresses": ["..."] }` (max 10) |
| GET | `/paper/summary` | Cash + positions overview |
| GET | `/paper/balance` | Cash balance |
| GET | `/paper/positions` | Open paper positions |
| GET | `/paper/trades` | Recent trades |
| POST | `/paper/trade` | Execute paper buy/sell |
| POST | `/paper/reset` | Reset paper account to $10k |

### Example: analyze a mint

```bash
curl -s http://localhost:8000/analyze/So11111111111111111111111111111111111111112 | jq .action,.confidence
```

### Example: paper buy

```bash
curl -s -X POST http://localhost:8000/paper/trade \
  -H 'Content-Type: application/json' \
  -d '{"token_address":"...","symbol":"MEME","side":"buy","usd_amount":50,"price":0.00012}'
```

---

## Project structure

```
solana-ai-trading-terminal/
├── backend/
│   ├── main.py                 # FastAPI app (v0.2)
│   ├── agents/
│   │   └── roles.py            # Technical, Risk, Sentiment, Narrative, Bull/Bear, Trader, RM
│   ├── analysis/
│   │   ├── pipeline.py         # Scoring + decision engine
│   │   └── schemas.py          # Pydantic Decision models
│   ├── data/
│   │   └── dexscreener.py      # DexScreener client + normalize
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── layout.tsx          # Wallet providers
│   │   ├── page.tsx            # Terminal UI
│   │   └── globals.css
│   ├── package.json
│   └── ...
├── LICENSE
└── README.md
```

---

## How decisions are made (high level)

1. Fetch best Solana pair for the mint (highest liquidity).
2. Normalize price, liquidity, volume (5m–24h), price change, tx buy/sell counts, age, boosts.
3. Run all specialist agents → text reports.
4. Compute:
   - Liquidity score (depth + liq/FDV penalty)
   - Volume momentum class
   - Holder/structural risk score + flags
   - Flow-based social proxy
   - Composite **edge score**
5. Apply **conservative policy** + Risk Manager vetoes → BUY / WATCH / AVOID.
6. Derive entry zone, stop, take-profits, and micro position size (capped vs pool).

BUY is rare by design. Thin, young, or dying-volume names are pushed to AVOID.

---

## Safety & limitations

- **Not financial advice.** Research tool only.
- No substitute for RugCheck, Solscan holder view, mint/freeze authority checks, or LP lock verification.
- Holder concentration is **not** fully available without Helius / Birdeye / similar — flags are structural proxies.
- Social sentiment is a **proxy** (price + order flow + profile links), not live Twitter/TG scraping.
- Paper ledger is **in-memory** (resets when the server restarts).
- Never connect a large mainnet wallet to experimental software.
- Never enable real trading until you fully understand and audit the execution path.

---

## Roadmap

- [ ] Optional LLM layer (OpenAI / Anthropic / xAI / Groq) on top of structured scores
- [ ] Helius / Birdeye / RugCheck integrations for real holder + authority data
- [ ] Live X sentiment module
- [ ] Persistent paper DB (SQLite/Postgres)
- [ ] Watchlist + alerts
- [ ] Jupiter quote integration (still user-signed only)
- [ ] Full LangGraph TradingAgents port for Solana tools
- [ ] Docker Compose one-command launch

---

## Adapting full TradingAgents

The `backend/agents/` package mirrors TradingAgents roles. To go further:

1. Install [TradingAgents](https://github.com/TauricResearch/TradingAgents) or a crypto fork.
2. Replace heuristic functions in `roles.py` with LangGraph agent nodes.
3. Register Solana tools (DexScreener, holder APIs, Jupiter quote) as tool calls.
4. Keep this repo’s **Decision schema** as the stable output contract for the UI.

---

## Contributing

PRs welcome for data sources, agent quality, tests, and UI. Please keep real-money execution opt-in, documented, and hard to enable by accident.

---

## Disclaimer

This software is provided for educational and research purposes only, **as-is**, without warranty of any kind. Cryptocurrency trading involves substantial risk of loss. Authors and contributors are not responsible for any financial losses or damages arising from use of this software.

## License

MIT
