"use client";

import { useState } from "react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Decision = {
  action: "BUY" | "WATCH" | "AVOID";
  confidence: number;
  liquidity_score: number;
  volume_momentum: string;
  holder_risk: { score: number; flags: string[]; notes: string };
  social_sentiment: string;
  technical_signals: string[];
  entry_zone: { low?: number; high?: number };
  stop_loss?: number;
  take_profit: number[];
  position_sizing: { pct_of_portfolio: number; max_usd: number; rationale: string };
  risk_reward?: number;
  explanation: string;
  token: { address?: string; name?: string; symbol?: string };
  market: any;
  timestamp: string;
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<any[]>([]);

  async function doSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setDecision(null);
    try {
      const r = await fetch(`${API}/tokens/search?q=${encodeURIComponent(query)}&limit=10`);
      if (!r.ok) throw new Error("Search failed");
      const data = await r.json();
      setSearchResults(data);
    } catch (e: any) {
      setError(e.message || "Search error");
    } finally {
      setLoading(false);
    }
  }

  async function analyze(address: string) {
    setLoading(true);
    setError(null);
    setDecision(null);
    try {
      const r = await fetch(`${API}/analyze/${address}`);
      if (!r.ok) {
        const t = await r.text();
        throw new Error(t || "Analysis failed");
      }
      const data = await r.json();
      setDecision(data);
    } catch (e: any) {
      setError(e.message || "Analysis error");
    } finally {
      setLoading(false);
    }
  }

  const actionClass =
    decision?.action === "BUY" ? "buy" : decision?.action === "WATCH" ? "watch" : "avoid";

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "1.5rem" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.5rem",
          gap: "1rem",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "1.5rem" }}>Solana AI Trading Terminal</h1>
          <p style={{ margin: "0.25rem 0 0", color: "var(--muted)", fontSize: "0.9rem" }}>
            Multi-agent analysis · Paper mode · Educational only
          </p>
        </div>
        <WalletMultiButton />
      </header>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <input
            placeholder="Search token name, symbol, or paste mint address..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doSearch()}
            style={{ flex: 1, minWidth: 220 }}
          />
          <button onClick={doSearch} disabled={loading}>
            {loading ? "Loading..." : "Search"}
          </button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginTop: "0.75rem" }}>
          Backend must be running at {API}. Real trading is disabled.
        </p>
      </div>

      {error && (
        <div className="card" style={{ borderColor: "var(--red)", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      <div className="grid grid-2">
        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Search Results</h2>
          {searchResults.length === 0 && (
            <p style={{ color: "var(--muted)" }}>Search for a Solana token to begin.</p>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            {searchResults.map((p) => (
              <button
                key={p.pair_address}
                onClick={() => analyze(p.base_token?.address)}
                style={{
                  textAlign: "left",
                  background: "#0f172a",
                  border: "1px solid var(--border)",
                }}
              >
                <strong>
                  {p.base_token?.symbol} / {p.quote_token?.symbol}
                </strong>{" "}
                <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                  · Liq ${Number(p.liquidity_usd || 0).toLocaleString()} · Vol $
                  {Number(p.volume?.h24 || 0).toLocaleString()}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>AI Analysis</h2>
          {!decision && (
            <p style={{ color: "var(--muted)" }}>
              Select a token to run the multi-agent pipeline (Technical, Risk, Sentiment,
              Narrative, Bull/Bear, Trader, Risk Manager).
            </p>
          )}
          {decision && (
            <div>
              <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", marginBottom: "1rem" }}>
                <span className={`badge ${actionClass}`}>{decision.action}</span>
                <span>
                  Confidence <strong>{decision.confidence}%</strong>
                </span>
                <span style={{ color: "var(--muted)" }}>
                  {decision.token.symbol} · {decision.token.name}
                </span>
              </div>

              <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1rem" }}>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Liquidity Score</div>
                  <strong>{decision.liquidity_score}/100</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Volume Momentum</div>
                  <strong>{decision.volume_momentum}</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Holder Risk Score</div>
                  <strong>{decision.holder_risk.score}/100</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Risk / Reward</div>
                  <strong>{decision.risk_reward ?? "—"}</strong>
                </div>
              </div>

              <p style={{ fontSize: "0.9rem" }}>
                <strong>Entry zone:</strong>{" "}
                {decision.entry_zone.low?.toPrecision(6)} – {decision.entry_zone.high?.toPrecision(6)}
                <br />
                <strong>Stop-loss:</strong> {decision.stop_loss?.toPrecision(6) ?? "—"}
                <br />
                <strong>Take-profit:</strong>{" "}
                {decision.take_profit.map((t) => t.toPrecision(6)).join(" / ") || "—"}
                <br />
                <strong>Max size:</strong> ${decision.position_sizing.max_usd} (
                {decision.position_sizing.pct_of_portfolio}% portfolio)
              </p>

              <h3 style={{ fontSize: "0.95rem" }}>Technical signals</h3>
              <ul style={{ marginTop: 0 }}>
                {decision.technical_signals.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>

              <h3 style={{ fontSize: "0.95rem" }}>AI Explanation</h3>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  fontSize: "0.82rem",
                  color: "var(--muted)",
                  background: "#0f172a",
                  padding: "0.75rem",
                  borderRadius: 8,
                  maxHeight: 320,
                  overflow: "auto",
                }}
              >
                {decision.explanation}
              </pre>

              <p style={{ fontSize: "0.8rem", color: "var(--muted)", marginTop: "1rem" }}>
                Paper trading only. Real execution is disabled in this release. Always DYOR.
              </p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
