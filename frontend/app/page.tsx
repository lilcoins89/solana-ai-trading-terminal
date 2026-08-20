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
  market: {
    price_usd?: number;
    liquidity_usd?: number;
    volume_h24?: number;
    price_change_h1?: number;
    price_change_h24?: number;
    buy_ratio_h1?: number;
    age_hours?: number;
    dex_id?: string;
    url?: string;
  };
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
      // If looks like a mint, analyze directly
      if (query.trim().length >= 32 && !query.includes(" ")) {
        await analyze(query.trim());
        setSearchResults([]);
        return;
      }
      const r = await fetch(`${API}/tokens/search?q=${encodeURIComponent(query)}&limit=12`);
      if (!r.ok) throw new Error("Search failed — is the backend running?");
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
    <main style={{ maxWidth: 1140, margin: "0 auto", padding: "1.5rem" }}>
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
            Multi-agent · v0.2 · Paper mode · Educational only
          </p>
        </div>
        <WalletMultiButton />
      </header>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <input
            placeholder="Search name/symbol or paste mint address..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doSearch()}
            style={{ flex: 1, minWidth: 240 }}
          />
          <button onClick={doSearch} disabled={loading}>
            {loading ? "Working..." : "Search / Analyze"}
          </button>
        </div>
        <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginTop: "0.75rem" }}>
          API: {API} · Real trading disabled · DYOR
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
            <p style={{ color: "var(--muted)" }}>
              Search a Solana token, or paste a mint and hit Analyze.
            </p>
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
                  {Number(p.volume?.h24 || 0).toLocaleString()} ·{" "}
                  {Number(p.price_change?.h24 || 0).toFixed(1)}% 24h
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>AI Analysis</h2>
          {!decision && (
            <p style={{ color: "var(--muted)" }}>
              Select a token to run Technical · Risk · Sentiment · Narrative · Bull/Bear ·
              Trader · Risk Manager.
            </p>
          )}
          {decision && (
            <div>
              <div
                style={{
                  display: "flex",
                  gap: "0.75rem",
                  alignItems: "center",
                  marginBottom: "1rem",
                  flexWrap: "wrap",
                }}
              >
                <span className={`badge ${actionClass}`}>{decision.action}</span>
                <span>
                  Confidence <strong>{decision.confidence}%</strong>
                </span>
                <span style={{ color: "var(--muted)" }}>
                  {decision.token.symbol} · {decision.token.name}
                </span>
                {decision.market?.url && (
                  <a href={decision.market.url} target="_blank" rel="noreferrer">
                    DexScreener ↗
                  </a>
                )}
              </div>

              <div
                className="grid"
                style={{ gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1rem" }}
              >
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Liquidity Score</div>
                  <strong>{decision.liquidity_score}/100</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Volume Momentum</div>
                  <strong>{decision.volume_momentum}</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Holder Risk</div>
                  <strong>{decision.holder_risk.score}/100</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Social Sentiment</div>
                  <strong>{decision.social_sentiment}</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Risk / Reward</div>
                  <strong>{decision.risk_reward ?? "—"}</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Pair Age</div>
                  <strong>
                    {decision.market?.age_hours != null
                      ? `${decision.market.age_hours}h`
                      : "—"}
                  </strong>
                </div>
              </div>

              {decision.holder_risk.flags?.length > 0 && (
                <p style={{ fontSize: "0.85rem" }}>
                  <strong>Flags:</strong> {decision.holder_risk.flags.join(", ")}
                </p>
              )}

              <p style={{ fontSize: "0.9rem" }}>
                <strong>Price:</strong> ${decision.market?.price_usd} ·{" "}
                <strong>Liq:</strong> ${Number(decision.market?.liquidity_usd || 0).toLocaleString()} ·{" "}
                <strong>24h:</strong> {Number(decision.market?.price_change_h24 || 0).toFixed(1)}% ·{" "}
                <strong>Buy ratio 1h:</strong>{" "}
                {decision.market?.buy_ratio_h1 != null
                  ? `${(decision.market.buy_ratio_h1 * 100).toFixed(0)}%`
                  : "—"}
                <br />
                <strong>Entry zone:</strong>{" "}
                {decision.entry_zone.low?.toPrecision(6)} –{" "}
                {decision.entry_zone.high?.toPrecision(6)}
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
                  maxHeight: 340,
                  overflow: "auto",
                }}
              >
                {decision.explanation}
              </pre>

              <p style={{ fontSize: "0.8rem", color: "var(--muted)", marginTop: "1rem" }}>
                Paper trading only. Not financial advice. Always verify mint authority, LP lock,
                and holders on Solscan / RugCheck.
              </p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
