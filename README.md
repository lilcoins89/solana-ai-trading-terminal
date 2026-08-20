# Solana AI Trading Terminal

> **Educational / Research Project Only**  
> Not financial advice. Solana memecoins are extremely high risk. Most tokens go to zero. Never risk money you cannot afford to lose. Real trading is disabled by default.

A layered AI Solana Trading Terminal inspired by [TradingAgents](https://github.com/TauricResearch/TradingAgents).

**Architecture**

```
Frontend (Next.js + Solana Wallet Adapter)
        │
Token Discovery (DexScreener)
        │
Market Data Layer
        │
AI Multi-Agent Engine (adapted TradingAgents roles)
  ├── Technical Analyst
  ├── On-chain Risk / Holder Analyst
  ├── Sentiment Analyst
  ├── Narrative / News Analyst
  ├── Bull vs Bear Researchers
  ├── Trader Agent
  └── Risk Manager → Final Decision
        │
Structured Output (Buy / Watch / Avoid + full metrics)
        │
Paper Trading (default)  |  Optional gated real execution
```

## Features

- Connect Solana wallet (Phantom, Solflare, etc.)
- Discover new / trending tokens via DexScreener
- Full AI analysis producing:
  - 🟢 Buy / 🟡 Watch / 🔴 Avoid
  - AI confidence
  - Liquidity score
  - Volume momentum
  - Holder / risk analysis
  - Social sentiment
  - Technical signals
  - Entry zone, Stop-loss, Take-profit
  - Position sizing & Risk/Reward
  - Detailed AI explanation
- Paper trading mode (default and recommended)
- Clean separation of concerns (no giant monolith)

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.11+
- (Optional) OpenAI / Anthropic / xAI / Groq API key for enhanced LLM reasoning

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\\Scripts\\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env if you want LLM enhancement
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Project Structure

```
solana-ai-trading-terminal/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── agents/                 # Multi-agent roles (TradingAgents style)
│   ├── data/                   # DexScreener + market data clients
│   ├── analysis/               # Orchestrator that runs the agent pipeline
│   ├── paper/                  # Paper trading ledger
│   └── requirements.txt
├── frontend/
│   ├── app/                    # Next.js App Router
│   ├── components/             # Wallet, TokenCard, AnalysisPanel
│   └── ...
├── docs/
└── README.md
```

## Safety First

- **Paper trading is the default.** Real execution requires explicit configuration and user confirmation.
- Never put large amounts or the private key of your main wallet into any trading system.
- Always verify token contracts yourself (RugCheck, Solscan, Birdeye, etc.).
- The AI can be wrong. Use outputs as one input among many.

## Adapting Full TradingAgents

The `backend/agents/` folder mirrors the specialized roles from TradingAgents:

- Fundamentals → On-chain / Tokenomics Analyst (adapted for memecoins)
- Sentiment Analyst
- Technical Analyst
- News / Narrative Analyst
- Bull / Bear Researchers
- Trader
- Risk Manager / Portfolio Manager

You can later replace the simplified sequential pipeline with a full LangGraph version of TradingAgents and inject Solana-specific tools (holder analysis, LP lock status, mint authority, etc.).

## Disclaimer

This software is provided for educational and research purposes only. The authors and contributors are not responsible for any financial losses. Cryptocurrency trading involves substantial risk of loss.

## License

MIT
