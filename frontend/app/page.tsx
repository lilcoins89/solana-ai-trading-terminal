"use client";

import { useState } from "react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Decision = {
  action: "BUY" | "WATCH" | "AVOID";
  confidence: number;
  liquidity_score: number;
  volume_momentum: string;
  holder_risk: {
    score: number;
    top1_pct?: number | null;
    top10_pct?: number | null;
    mint_authority_renounced?: boolean | null;
    freeze_authority_renounced?: boolean | null;
    helius_configured?: boolean;
    flags: string[];
  };
  cross_check?: {
    lp_locked_pct?: number | null;
    sniper_or_insider_suspected?: boolean;
    rugcheck_ok?: boolean;
    risks?: { name?: string; level?: string }[];
    links?: Record<string, string>;
    notes?: string;
  };
  social_sentiment: string;
  technical_signals: string[];
  entry_zone: { low?: number; high?: number };
  stop_loss?: number;
  take_profit: number[];
  position_sizing: { pct_of_portfolio: number; max_usd: number };
  risk_reward?: number;
  explanation: string;
  token: { address?: string; name?: string; symbol?: string };
  market: any;
};

function authLabel(v?: boolean | null) {
  if (v === true) return "Renounced ✓";
  if (v === false) return "ACTIVE ⚠";
  return "Unknown";
}

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
      if (query.trim().length >= 32 && !query.includes(" ")) {
        await analyze(query.trim());
        setSearchResults([]);
        return;
      }
      const r = await fetch(`${API}/tokens/search?q=${encodeURIComponent(query)}&limit=12`);
      if (!r.ok) throw new Error("Search failed — is the backend running?");
      setSearchResults(await r.json());
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
      if (!r.ok) throw new Error((await r.text()) || "Analysis failed");
      setDecision(await r.json());
    } catch (e: any) {
      setError(e.message || "Analysis error");
    } finally {
      setLoading(false);
    }
  }

  const actionClass =
    decision?.action === "BUY" ? "buy" : decision?.action === "WATCH" ? "watch" : "avoid";
  const cc = decision?.cross_check;

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
            Multi-agent · Helius · RugCheck · Solscan · v0.4 · Paper only
          </p>
        </div>
        <WalletMultiButton />
      </header>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <input
            placeholder="Search name/symbol or paste mint..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doSearch()}
            style={{ flex: 1, minWidth: 240 }}
          />
          <button onClick={doSearch} disabled={loading}>
            {loading ? "Working..." : "Search / Analyze"}
          </button>
        </div>
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
            <p style={{ color: "var(--muted)" }}>Search or paste a mint to analyze.</p>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            {searchResults.map((p) => (
              <button
                key={p.pair_address}
                onClick={() => analyze(p.base_token?.address)}
                style={{ textAlign: "left", background: "#0f172a", border: "1px solid var(--border)" }}
              >
                <strong>
                  {p.base_token?.symbol} / {p.quote_token?.symbol}
                </strong>{" "}
                <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                  · Liq ${Number(p.liquidity_usd || 0).toLocaleString()}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>AI Analysis</h2>
          {!decision && <p style={{ color: "var(--muted)" }}>Select a token to run the full pipeline.</p>}
          {decision && (
            <div>
              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
                <span className={`badge ${actionClass}`}>{decision.action}</span>
                <span>
                  Confidence <strong>{decision.confidence}%</strong>
                </span>
                <span style={{ color: "var(--muted)" }}>
                  {decision.token.symbol}
                </span>
              </div>

              <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>LP locked (RugCheck)</div>
                  <strong>
                    {cc?.lp_locked_pct != null ? `${cc.lp_locked_pct}%` : "n/a"}
                  </strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Sniper / insider</div>
                  <strong>{cc?.sniper_or_insider_suspected ? "Suspected ⚠" : "Not flagged"}</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Holder risk</div>
                  <strong>{decision.holder_risk.score}/100</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Top-10</div>
                  <strong>
                    {decision.holder_risk.top10_pct != null
                      ? `${decision.holder_risk.top10_pct}%`
                      : "—"}
                  </strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Mint auth</div>
                  <strong>{authLabel(decision.holder_risk.mint_authority_renounced)}</strong>
                </div>
                <div>
                  <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Freeze auth</div>
                  <strong>{authLabel(decision.holder_risk.freeze_authority_renounced)}</strong>
                </div>
              </div>

              <p style={{ fontSize: "0.9rem", marginTop: "0.75rem" }}>
                {cc?.links?.rugcheck && (
                  <>
                    <a href={cc.links.rugcheck} target="_blank" rel="noreferrer">
                      RugCheck ↗
                    </a>{" "}
                  </>
                )}
                {(cc?.links?.solscan_holders || cc?.links?.solscan) && (
                  <a
                    href={cc.links.solscan_holders || cc.links.solscan}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Solscan holders ↗
                  </a>
                )}
              </p>

              {cc?.risks && cc.risks.length > 0 && (
                <>
                  <h3 style={{ fontSize: "0.95rem" }}>RugCheck risks</h3>
                  <ul style={{ marginTop: 0 }}>
                    {cc.risks.slice(0, 6).map((r, i) => (
                      <li key={i}>
                        [{r.level}] {r.name}
                      </li>
                    ))}
                  </ul>
                </>
              )}

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
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
