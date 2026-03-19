import { useState, useEffect, useRef, useCallback } from "react";

const API = "";

const MOCK_STATE = {
  run_id: null,
  ticker: "",
  company_name: "",
  status: "idle",
  current_stage: null,
  completed_stages: [],
  overall_confidence: 0,
  hitl_required: false,
  hitl_packet: null,
  final_report: null,
  financial_metrics: null,
  sentiment_signals: [],
  risk_flags: [],
  peer_comparison: null,
  activity_log: [],
  errors: [],
  market_snapshot: null,
  recent_runs: [],
};

const STAGES = [
  { id: "ingestion",   label: "INGEST",    icon: "▼" },
  { id: "extraction",  label: "EXTRACT",   icon: "◈" },
  { id: "planning",    label: "PLAN",      icon: "◉" },
  { id: "analysis",    label: "ANALYZE",   icon: "◆" },
  { id: "synthesis",   label: "SYNTHESIZE",icon: "◎" },
  { id: "fact_check",  label: "VERIFY",    icon: "✓" },
  { id: "hitl_review", label: "REVIEW",    icon: "⊕" },
  { id: "report",      label: "REPORT",    icon: "▣" },
];

const MOCK_ACTIVITY = [
  { agent: "DocumentIngester",  msg: "Fetching 10-K, 10-Q, 8-K filings from SEC EDGAR..." },
  { agent: "DocumentIngester",  msg: "Market snapshot acquired — AAPL $227.48 (+0.82%)" },
  { agent: "MultimodalExtractor", msg: "Extracted 847 chunks, 23 tables, 11 figures" },
  { agent: "MultimodalExtractor", msg: "Vision LLM interpreting revenue bar chart..." },
  { agent: "ResearchPlanner",   msg: "4 sub-analyses scheduled: financial, sentiment, risk, peers" },
  { agent: "ResearchPlanner",   msg: "Retrieved 38 context chunks from Pinecone [COSINE≥0.72]" },
  { agent: "FinancialAnalyst",  msg: "Revenue: $94.9B (+6.1% YoY) | Operating margin: 31.7%" },
  { agent: "FinancialAnalyst",  msg: "EPS: $1.64 — beat consensus $1.59 by +3.1%" },
  { agent: "SentimentAnalyst",  msg: "Management tone: BULLISH (score: +0.61)" },
  { agent: "SentimentAnalyst",  msg: "Detected 3 HEDGING signals in Q&A section" },
  { agent: "RiskAssessor",      msg: "4 risk flags: 1 HIGH (regulatory), 3 MEDIUM" },
  { agent: "PeerComparator",    msg: "AAPL ranks 78th percentile on P/E vs MSFT, GOOG, META" },
  { agent: "Synthesizer",       msg: "Generating investment memo (1,240 words)..." },
  { agent: "FactChecker",       msg: "Verified 12/14 claims — 2 flagged for review" },
  { agent: "HITLGateway",       msg: "Confidence 0.68 < threshold 0.80 → human review required" },
];

const MOCK_METRICS = {
  ticker: "AAPL", period: "Q4 FY2024",
  revenue: 94900, revenue_growth_yoy: 0.061,
  gross_margin: 0.462, operating_margin: 0.317, net_margin: 0.236,
  eps: 1.64, eps_beat: 3.14,
  fcf: 26800, debt_to_equity: 1.87,
  current_ratio: 0.87, roe: 1.47,
  pe_ratio: 30.2, ev_ebitda: 23.1,
};

const MOCK_RISKS = [
  { category: "regulatory", severity: "high",     description: "EU Digital Markets Act compliance costs estimated $2-4B annually" },
  { category: "market",     severity: "medium",   description: "China revenue exposure 18% — geopolitical headwind" },
  { category: "operational",severity: "medium",   description: "Supply chain concentration in TSMC 3nm node" },
  { category: "ESG",        severity: "low",      description: "Carbon neutrality targets require $1.5B investment through 2030" },
];

const MOCK_SENTIMENT = [
  { source: "management_opening", score: 0.71, label: "bullish",  confidence: 0.88 },
  { source: "guidance_section",   score: 0.45, label: "bullish",  confidence: 0.79 },
  { source: "analyst_questions",  score: 0.12, label: "neutral",  confidence: 0.72 },
  { source: "management_qa",      score: 0.38, label: "bullish",  confidence: 0.81 },
];

const SEVERITY_COLOR = { critical: "#ff4444", high: "#ff8c00", medium: "#f0c040", low: "#4caf50" };
const SENTIMENT_COLOR = { bullish: "#4caf50", bearish: "#ff4444", neutral: "#888", mixed: "#f0c040" };

export default function App() {
  const [state, setState] = useState(MOCK_STATE);
  const [ticker, setTicker] = useState("");
  const [researchType, setResearchType] = useState("earnings_analysis");
  const [activeTab, setActiveTab] = useState("overview");
  const [demoMode, setDemoMode] = useState(false);
  const [animIdx, setAnimIdx] = useState(0);
  const [reviewForm, setReviewForm] = useState({ decision: "approved", notes: "" });
  const [memoExpanded, setMemoExpanded] = useState(false);
  const wsRef = useRef(null);
  const activityRef = useRef(null);
  const demoTimerRef = useRef(null);

  const addActivity = useCallback((agent, msg) => {
    setState(s => ({
      ...s,
      activity_log: [...s.activity_log.slice(-80), {
        agent, msg, ts: new Date().toLocaleTimeString("en-US", { hour12: false })
      }]
    }));
    setTimeout(() => {
      if (activityRef.current) activityRef.current.scrollTop = activityRef.current.scrollHeight;
    }, 50);
  }, []);

  const runDemo = useCallback(() => {
    setDemoMode(true);
    setTicker("AAPL");
    setState(s => ({
      ...s, ticker: "AAPL", company_name: "Apple Inc.", status: "running",
      run_id: "demo-" + Date.now(), current_stage: "ingestion",
      completed_stages: [], activity_log: [], overall_confidence: 0,
      financial_metrics: null, sentiment_signals: [], risk_flags: [],
    }));

    let stageIdx = 0;
    let actIdx = 0;
    const stageMap = ["ingestion","ingestion","extraction","extraction","planning","planning",
                      "analysis","analysis","analysis","analysis","analysis","analysis",
                      "synthesis","fact_check","hitl_review"];

    const tick = () => {
      if (actIdx >= MOCK_ACTIVITY.length) {
        setState(s => ({
          ...s, status: "awaiting_review", current_stage: "hitl_review",
          hitl_required: true, overall_confidence: 0.68,
          completed_stages: STAGES.slice(0,6).map(s=>s.id),
          financial_metrics: MOCK_METRICS,
          sentiment_signals: MOCK_SENTIMENT,
          risk_flags: MOCK_RISKS,
        }));
        setActiveTab("hitl");
        return;
      }
      const item = MOCK_ACTIVITY[actIdx];
      addActivity(item.agent, item.msg);
      const stage = stageMap[actIdx] || "analysis";
      setState(s => ({
        ...s, current_stage: stage,
        completed_stages: stageMap.slice(0, actIdx).filter((v,i,a)=>a.indexOf(v)===i),
        overall_confidence: Math.min(0.68, actIdx * 0.05),
        financial_metrics: actIdx >= 8 ? MOCK_METRICS : s.financial_metrics,
        sentiment_signals: actIdx >= 10 ? MOCK_SENTIMENT : s.sentiment_signals,
        risk_flags: actIdx >= 11 ? MOCK_RISKS : s.risk_flags,
      }));
      actIdx++;
      demoTimerRef.current = setTimeout(tick, 900 + Math.random() * 600);
    };
    demoTimerRef.current = setTimeout(tick, 400);
  }, [addActivity]);

  useEffect(() => () => clearTimeout(demoTimerRef.current), []);

  const submitHITL = () => {
    addActivity("HITLGateway", `Review submitted: ${reviewForm.decision.toUpperCase()} — "${reviewForm.notes}"`);
    setState(s => ({
      ...s, status: "complete", current_stage: "report",
      completed_stages: STAGES.map(s=>s.id),
      overall_confidence: reviewForm.decision === "approved" ? 0.91 : 0.62,
      hitl_required: false,
      final_report: {
        ticker: "AAPL", generated_at: new Date().toISOString(),
        confidence_score: 0.91,
        memo: MOCK_MEMO,
        hitl_reviewed: true,
        reviewer: "analyst@capitalmind.ai",
      }
    }));
    setActiveTab("report");
  };

  const confidence = state.overall_confidence;
  const confColor = confidence >= 0.8 ? "#4caf50" : confidence >= 0.6 ? "#f0c040" : "#ff8c00";

  return (
    <div style={{ fontFamily: "'IBM Plex Mono', 'Courier New', monospace", background: "#0a0c10", color: "#c8cdd8", minHeight: "100vh", fontSize: 12 }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #2a3040; border-radius: 2px; }
        input, select, textarea { background: #0d1117; color: #c8cdd8; border: 1px solid #1e2535; border-radius: 3px; padding: 6px 10px; font-family: inherit; font-size: 12px; outline: none; }
        input:focus, select:focus, textarea:focus { border-color: #3d7bd8; }
        button { cursor: pointer; font-family: inherit; font-size: 11px; border-radius: 2px; border: none; }
        .tab { background: transparent; color: #6b7585; padding: 6px 14px; border-bottom: 2px solid transparent; letter-spacing: 0.08em; font-size: 10px; font-weight: 500; }
        .tab.active { color: #e2e8f0; border-bottom-color: #3d7bd8; }
        .tab:hover { color: #c8cdd8; }
        .metric-card { background: #0d1117; border: 1px solid #1a2035; border-radius: 4px; padding: 10px 14px; }
        .label { color: #4a5568; font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px; }
        .value { color: #e2e8f0; font-size: 18px; font-weight: 500; font-family: 'IBM Plex Sans', sans-serif; }
        .value-sm { color: #e2e8f0; font-size: 13px; font-weight: 500; }
        .pos { color: #4caf50; }
        .neg { color: #f44336; }
        .pill { display: inline-block; padding: 2px 7px; border-radius: 2px; font-size: 9px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; }
        .bar-bg { background: #1a2035; border-radius: 2px; height: 4px; }
        .bar-fill { height: 4px; border-radius: 2px; transition: width 0.6s ease; }
        .agent-badge { background: #1a2035; color: #3d7bd8; padding: 1px 6px; border-radius: 2px; font-size: 9px; letter-spacing: 0.08em; }
        .btn-primary { background: #3d7bd8; color: #fff; padding: 8px 18px; letter-spacing: 0.08em; font-weight: 500; }
        .btn-primary:hover { background: #2d6bc8; }
        .btn-ghost { background: transparent; color: #6b7585; border: 1px solid #1e2535; padding: 6px 14px; letter-spacing: 0.06em; }
        .btn-ghost:hover { border-color: #3d7bd8; color: #c8cdd8; }
        .btn-success { background: #1b4a2a; color: #4caf50; border: 1px solid #2d7a3d; padding: 7px 16px; letter-spacing: 0.06em; }
        .btn-danger { background: #4a1b1b; color: #f44336; border: 1px solid #7a2d2d; padding: 7px 16px; letter-spacing: 0.06em; }
        .pulse { animation: pulse 1.5s ease-in-out infinite; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        .blink { animation: blink 1s step-start infinite; }
        @keyframes blink { 50%{opacity:0} }
        .slide-in { animation: slidein 0.3s ease; }
        @keyframes slidein { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:none} }
      `}</style>

      {/* ── Top Bar ────────────────────────────────────────────────────────── */}
      <div style={{ background: "#060810", borderBottom: "1px solid #1a2035", padding: "0 20px", display: "flex", alignItems: "center", height: 44, gap: 20 }}>
        <span style={{ color: "#3d7bd8", fontWeight: 600, fontSize: 13, letterSpacing: "0.15em" }}>CAPITALMIND</span>
        <span style={{ color: "#1e2535", fontSize: 18 }}>│</span>
        <span style={{ color: "#4a5568", fontSize: 10, letterSpacing: "0.1em" }}>INVESTMENT INTELLIGENCE PLATFORM</span>
        <div style={{ flex: 1 }} />
        {state.status !== "idle" && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: state.status === "running" ? "#f0c040" : state.status === "complete" ? "#4caf50" : state.status === "awaiting_review" ? "#ff8c00" : "#4a5568" }} className={state.status === "running" ? "pulse" : ""} />
            <span style={{ color: "#4a5568", fontSize: 10, letterSpacing: "0.08em" }}>
              {state.status === "running" ? "PROCESSING" : state.status === "complete" ? "COMPLETE" : state.status === "awaiting_review" ? "AWAITING REVIEW" : "IDLE"}
            </span>
            {state.ticker && <span style={{ color: "#3d7bd8", fontWeight: 600 }}>{state.ticker}</span>}
          </div>
        )}
        <span style={{ color: "#4a5568", fontSize: 10 }}>{new Date().toLocaleTimeString("en-US", { hour12: false })} EST</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr 280px", height: "calc(100vh - 44px)" }}>

        {/* ── LEFT PANEL: Control + Activity ──────────────────────────────── */}
        <div style={{ borderRight: "1px solid #1a2035", display: "flex", flexDirection: "column", overflow: "hidden" }}>

          {/* Research Form */}
          <div style={{ padding: "14px 16px", borderBottom: "1px solid #1a2035" }}>
            <div style={{ color: "#4a5568", fontSize: 9, letterSpacing: "0.12em", marginBottom: 12 }}>NEW RESEARCH RUN</div>

            <div style={{ marginBottom: 8 }}>
              <div className="label">TICKER</div>
              <input value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())}
                placeholder="AAPL" style={{ width: "100%", textTransform: "uppercase", fontWeight: 600, fontSize: 14 }} />
            </div>

            <div style={{ marginBottom: 12 }}>
              <div className="label">ANALYSIS TYPE</div>
              <select value={researchType} onChange={e => setResearchType(e.target.value)} style={{ width: "100%" }}>
                <option value="earnings_analysis">Earnings Analysis</option>
                <option value="full_deep_dive">Full Deep Dive</option>
                <option value="risk_assessment">Risk Assessment</option>
                <option value="peer_comparison">Peer Comparison</option>
                <option value="quick_summary">Quick Summary</option>
              </select>
            </div>

            <div style={{ display: "flex", gap: 6 }}>
              <button className="btn-primary" style={{ flex: 1 }} onClick={runDemo}>
                RUN ANALYSIS ↗
              </button>
              <button className="btn-ghost" onClick={() => setState(MOCK_STATE)}>CLR</button>
            </div>
          </div>

          {/* Pipeline Stage Tracker */}
          <div style={{ padding: "12px 16px", borderBottom: "1px solid #1a2035" }}>
            <div className="label" style={{ marginBottom: 10 }}>PIPELINE STAGES</div>
            {STAGES.map((s, i) => {
              const done = state.completed_stages?.includes(s.id);
              const active = state.current_stage === s.id;
              return (
                <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <div style={{ width: 18, height: 18, borderRadius: 2, background: done ? "#1b4a2a" : active ? "#1a2a4a" : "#0d1117", border: `1px solid ${done ? "#2d7a3d" : active ? "#3d7bd8" : "#1a2035"}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: done ? "#4caf50" : active ? "#3d7bd8" : "#2a3040" }} className={active ? "pulse" : ""}>
                    {done ? "✓" : s.icon}
                  </div>
                  <span style={{ fontSize: 9, letterSpacing: "0.1em", color: done ? "#4caf50" : active ? "#c8cdd8" : "#2a3040", fontWeight: active || done ? 500 : 400 }}>{s.label}</span>
                  {active && <span style={{ marginLeft: "auto", fontSize: 8, color: "#3d7bd8" }} className="blink">●</span>}
                </div>
              );
            })}
          </div>

          {/* Agent Activity Feed */}
          <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
            <div style={{ padding: "10px 16px", borderBottom: "1px solid #1a2035", display: "flex", alignItems: "center", gap: 6 }}>
              <div className="label" style={{ margin: 0 }}>AGENT ACTIVITY</div>
              {state.status === "running" && <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#f0c040", marginLeft: "auto" }} className="pulse" />}
            </div>
            <div ref={activityRef} style={{ flex: 1, overflowY: "auto", padding: "8px 12px" }}>
              {state.activity_log.length === 0 ? (
                <div style={{ color: "#2a3040", fontSize: 10, textAlign: "center", marginTop: 20 }}>Awaiting run...</div>
              ) : state.activity_log.map((ev, i) => (
                <div key={i} className="slide-in" style={{ marginBottom: 8, borderLeft: "2px solid #1a2035", paddingLeft: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 2 }}>
                    <span className="agent-badge">{ev.agent.replace(/Agent$/,"").toUpperCase()}</span>
                    <span style={{ color: "#2a3040", fontSize: 8, marginLeft: "auto" }}>{ev.ts}</span>
                  </div>
                  <div style={{ color: "#8899aa", fontSize: 10, lineHeight: 1.5 }}>{ev.msg}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── MAIN PANEL ──────────────────────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>

          {/* Tabs */}
          <div style={{ borderBottom: "1px solid #1a2035", display: "flex", alignItems: "center", padding: "0 20px", background: "#060810" }}>
            {[
              { id: "overview",  label: "OVERVIEW" },
              { id: "financial", label: "FINANCIALS" },
              { id: "risk",      label: "RISK FLAGS" },
              { id: "sentiment", label: "SENTIMENT" },
              { id: "hitl",      label: state.hitl_required ? "⚠ REVIEW" : "REVIEW" },
              { id: "report",    label: "MEMO" },
              { id: "audit",     label: "AUDIT TRAIL" },
            ].map(t => (
              <button key={t.id} className={`tab ${activeTab === t.id ? "active" : ""}`}
                onClick={() => setActiveTab(t.id)}
                style={{ color: t.id === "hitl" && state.hitl_required ? "#ff8c00" : undefined }}>
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>

            {/* ── OVERVIEW TAB ─────────────────────────────────────────────── */}
            {activeTab === "overview" && (
              <div>
                {state.status === "idle" ? (
                  <div style={{ textAlign: "center", marginTop: 60 }}>
                    <div style={{ color: "#1e2535", fontSize: 64, marginBottom: 20 }}>◈</div>
                    <div style={{ color: "#2a3040", fontSize: 13, letterSpacing: "0.1em", marginBottom: 8 }}>READY FOR ANALYSIS</div>
                    <div style={{ color: "#1e2535", fontSize: 10 }}>Enter a ticker and run analysis to begin</div>
                    <button className="btn-primary" style={{ marginTop: 24, padding: "10px 28px" }} onClick={runDemo}>
                      RUN AAPL DEMO ↗
                    </button>
                  </div>
                ) : (
                  <div>
                    {/* Header */}
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 20, marginBottom: 24 }}>
                      <div>
                        <div style={{ fontSize: 32, fontWeight: 600, color: "#e2e8f0", fontFamily: "'IBM Plex Sans', sans-serif", letterSpacing: "-0.02em" }}>
                          {state.ticker || ticker}
                        </div>
                        <div style={{ color: "#4a5568", fontSize: 11, marginTop: 2 }}>{state.company_name || "—"}</div>
                      </div>
                      <div style={{ marginLeft: "auto", textAlign: "right" }}>
                        <div className="label">CONFIDENCE SCORE</div>
                        <div style={{ fontSize: 28, fontWeight: 600, color: confColor, fontFamily: "'IBM Plex Sans', sans-serif" }}>
                          {(confidence * 100).toFixed(0)}%
                        </div>
                        <div style={{ width: 100, marginLeft: "auto", marginTop: 4 }}>
                          <div className="bar-bg">
                            <div className="bar-fill" style={{ width: `${confidence * 100}%`, background: confColor }} />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Status Banner */}
                    {state.status === "awaiting_review" && (
                      <div style={{ background: "#2a1a06", border: "1px solid #8c4e00", borderRadius: 4, padding: "12px 16px", marginBottom: 20, display: "flex", alignItems: "center", gap: 10 }}>
                        <span style={{ fontSize: 16 }}>⚠</span>
                        <div>
                          <div style={{ color: "#f0a040", fontWeight: 500, fontSize: 11 }}>HUMAN REVIEW REQUIRED</div>
                          <div style={{ color: "#8c6030", fontSize: 10, marginTop: 2 }}>Confidence below threshold (0.68 &lt; 0.80). Switch to REVIEW tab to approve or reject.</div>
                        </div>
                        <button className="btn-primary" style={{ marginLeft: "auto" }} onClick={() => setActiveTab("hitl")}>
                          REVIEW NOW →
                        </button>
                      </div>
                    )}

                    {/* Key Metrics Grid */}
                    {state.financial_metrics && (
                      <div>
                        <div className="label" style={{ marginBottom: 10 }}>KEY METRICS — {state.financial_metrics.period}</div>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 20 }}>
                          {[
                            { label: "REVENUE", value: `$${(state.financial_metrics.revenue/1000).toFixed(1)}B`, sub: `${state.financial_metrics.revenue_growth_yoy > 0 ? "+" : ""}${(state.financial_metrics.revenue_growth_yoy * 100).toFixed(1)}% YoY`, pos: state.financial_metrics.revenue_growth_yoy > 0 },
                            { label: "OP. MARGIN", value: `${(state.financial_metrics.operating_margin * 100).toFixed(1)}%`, sub: "operating", pos: state.financial_metrics.operating_margin > 0.2 },
                            { label: "EPS", value: `$${state.financial_metrics.eps}`, sub: `${state.financial_metrics.eps_beat > 0 ? "+" : ""}${state.financial_metrics.eps_beat?.toFixed(1)}% vs est.`, pos: state.financial_metrics.eps_beat > 0 },
                            { label: "P/E RATIO", value: `${state.financial_metrics.pe_ratio}×`, sub: "trailing twelve months", pos: null },
                          ].map((m, i) => (
                            <div key={i} className="metric-card">
                              <div className="label">{m.label}</div>
                              <div className="value">{m.value}</div>
                              <div style={{ fontSize: 10, marginTop: 4, color: m.pos === true ? "#4caf50" : m.pos === false ? "#f44336" : "#4a5568" }}>{m.sub}</div>
                            </div>
                          ))}
                        </div>

                        {/* Risk Summary */}
                        <div className="label" style={{ marginBottom: 8 }}>RISK SUMMARY</div>
                        <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
                          {["critical","high","medium","low"].map(sev => {
                            const count = state.risk_flags.filter(r => r.severity === sev).length;
                            return count > 0 ? (
                              <div key={sev} style={{ background: `${SEVERITY_COLOR[sev]}18`, border: `1px solid ${SEVERITY_COLOR[sev]}40`, borderRadius: 3, padding: "4px 10px", display: "flex", gap: 6, alignItems: "center" }}>
                                <span style={{ fontWeight: 600, fontSize: 13, color: SEVERITY_COLOR[sev] }}>{count}</span>
                                <span style={{ fontSize: 9, color: SEVERITY_COLOR[sev], letterSpacing: "0.1em" }}>{sev.toUpperCase()}</span>
                              </div>
                            ) : null;
                          })}
                          {state.risk_flags.length === 0 && <span style={{ color: "#2a3040", fontSize: 10 }}>No flags yet</span>}
                        </div>

                        {/* Sentiment Bar */}
                        {state.sentiment_signals.length > 0 && (
                          <div>
                            <div className="label" style={{ marginBottom: 8 }}>SENTIMENT SIGNALS</div>
                            {state.sentiment_signals.map((sig, i) => (
                              <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                                <div style={{ width: 100, fontSize: 9, color: "#4a5568", letterSpacing: "0.06em" }}>{sig.source.replace(/_/g," ").toUpperCase()}</div>
                                <div style={{ flex: 1 }}>
                                  <div className="bar-bg">
                                    <div className="bar-fill" style={{
                                      width: `${Math.abs(sig.score) * 100}%`,
                                      background: SENTIMENT_COLOR[sig.label],
                                      marginLeft: sig.score < 0 ? `${(1 - Math.abs(sig.score)) * 100}%` : 0
                                    }} />
                                  </div>
                                </div>
                                <span style={{ fontSize: 10, color: SENTIMENT_COLOR[sig.label], width: 55, textAlign: "right" }}>{sig.label.toUpperCase()}</span>
                                <span style={{ fontSize: 10, color: "#4a5568", width: 30, textAlign: "right" }}>{(sig.score > 0 ? "+" : "") + sig.score.toFixed(2)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {state.status === "running" && !state.financial_metrics && (
                      <div style={{ color: "#2a3040", fontSize: 11, textAlign: "center", marginTop: 40 }}>
                        <div className="pulse" style={{ fontSize: 32, marginBottom: 12 }}>◈</div>
                        <div>Analysis in progress — {state.current_stage?.replace(/_/g," ").toUpperCase()}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ── FINANCIALS TAB ───────────────────────────────────────────── */}
            {activeTab === "financial" && (
              <div>
                <div className="label" style={{ marginBottom: 16 }}>FINANCIAL METRICS — {state.financial_metrics?.period || "—"}</div>
                {!state.financial_metrics ? (
                  <div style={{ color: "#2a3040", fontSize: 10 }}>No financial data yet. Run an analysis.</div>
                ) : (
                  <div>
                    {/* Income Statement */}
                    <div style={{ marginBottom: 20 }}>
                      <div style={{ color: "#3d7bd8", fontSize: 9, letterSpacing: "0.12em", marginBottom: 10 }}>INCOME STATEMENT</div>
                      <table style={{ width: "100%", borderCollapse: "collapse" }}>
                        <tbody>
                          {[
                            ["Revenue",         `$${(state.financial_metrics.revenue/1000).toFixed(2)}B`, `${state.financial_metrics.revenue_growth_yoy > 0 ? "+" : ""}${(state.financial_metrics.revenue_growth_yoy * 100).toFixed(1)}% YoY`, state.financial_metrics.revenue_growth_yoy > 0],
                            ["Gross Margin",     `${(state.financial_metrics.gross_margin * 100).toFixed(1)}%`, "of revenue", null],
                            ["Operating Margin", `${(state.financial_metrics.operating_margin * 100).toFixed(1)}%`, "EBIT/Revenue", state.financial_metrics.operating_margin > 0.25],
                            ["Net Margin",       `${(state.financial_metrics.net_margin * 100).toFixed(1)}%`, "net income/revenue", null],
                            ["EPS (reported)",   `$${state.financial_metrics.eps}`, `${state.financial_metrics.eps_beat > 0 ? "BEAT" : "MISSED"} by ${Math.abs(state.financial_metrics.eps_beat).toFixed(1)}%`, state.financial_metrics.eps_beat > 0],
                            ["Free Cash Flow",   `$${(state.financial_metrics.fcf/1000).toFixed(1)}B`, "operating — capex", null],
                          ].map(([label, val, sub, pos], i) => (
                            <tr key={i} style={{ borderBottom: "1px solid #1a2035" }}>
                              <td style={{ padding: "8px 0", color: "#4a5568", fontSize: 10, width: "35%" }}>{label}</td>
                              <td style={{ padding: "8px 0", color: "#e2e8f0", fontSize: 13, fontWeight: 500, width: "30%", fontFamily: "'IBM Plex Sans', sans-serif" }}>{val}</td>
                              <td style={{ padding: "8px 0", fontSize: 9, textAlign: "right", color: pos === true ? "#4caf50" : pos === false ? "#f44336" : "#4a5568" }}>{sub}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Balance Sheet & Valuation */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                      <div>
                        <div style={{ color: "#3d7bd8", fontSize: 9, letterSpacing: "0.12em", marginBottom: 10 }}>BALANCE SHEET</div>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <tbody>
                            {[
                              ["Debt / Equity",   state.financial_metrics.debt_to_equity?.toFixed(2)],
                              ["Current Ratio",   state.financial_metrics.current_ratio?.toFixed(2)],
                              ["Return on Equity",`${((state.financial_metrics.roe || 0) * 100).toFixed(0)}%`],
                            ].map(([l, v], i) => (
                              <tr key={i} style={{ borderBottom: "1px solid #1a2035" }}>
                                <td style={{ padding: "7px 0", color: "#4a5568", fontSize: 10 }}>{l}</td>
                                <td style={{ padding: "7px 0", color: "#e2e8f0", fontSize: 12, fontWeight: 500, textAlign: "right" }}>{v}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div>
                        <div style={{ color: "#3d7bd8", fontSize: 9, letterSpacing: "0.12em", marginBottom: 10 }}>VALUATION</div>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <tbody>
                            {[
                              ["P/E Ratio",      `${state.financial_metrics.pe_ratio}×`],
                              ["EV/EBITDA",      `${state.financial_metrics.ev_ebitda}×`],
                              ["Analyst Rating", "BUY (27) | HOLD (9) | SELL (2)"],
                            ].map(([l, v], i) => (
                              <tr key={i} style={{ borderBottom: "1px solid #1a2035" }}>
                                <td style={{ padding: "7px 0", color: "#4a5568", fontSize: 10 }}>{l}</td>
                                <td style={{ padding: "7px 0", color: "#e2e8f0", fontSize: 10, fontWeight: 500, textAlign: "right" }}>{v}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── RISK FLAGS TAB ───────────────────────────────────────────── */}
            {activeTab === "risk" && (
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                  <div className="label" style={{ margin: 0 }}>MATERIAL RISK FLAGS</div>
                  <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                    {["critical","high","medium","low"].map(s => (
                      <span key={s} className="pill" style={{ background: `${SEVERITY_COLOR[s]}20`, color: SEVERITY_COLOR[s] }}>
                        {state.risk_flags.filter(r => r.severity === s).length} {s}
                      </span>
                    ))}
                  </div>
                </div>
                {state.risk_flags.length === 0 ? (
                  <div style={{ color: "#2a3040", fontSize: 10 }}>No risk flags yet.</div>
                ) : state.risk_flags.map((flag, i) => (
                  <div key={i} style={{ borderLeft: `3px solid ${SEVERITY_COLOR[flag.severity]}`, paddingLeft: 14, marginBottom: 16, paddingBottom: 14, borderBottom: "1px solid #1a2035" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <span className="pill" style={{ background: `${SEVERITY_COLOR[flag.severity]}20`, color: SEVERITY_COLOR[flag.severity] }}>{flag.severity.toUpperCase()}</span>
                      <span className="pill" style={{ background: "#1a2035", color: "#6b7585" }}>{flag.category.toUpperCase()}</span>
                    </div>
                    <div style={{ color: "#c8cdd8", fontSize: 11, lineHeight: 1.6, marginBottom: 8 }}>{flag.description}</div>
                    {flag.evidence?.map((e, j) => (
                      <div key={j} style={{ color: "#4a5568", fontSize: 9, fontStyle: "italic", borderLeft: "1px solid #1a2035", paddingLeft: 8, marginBottom: 3 }}>"{e}"</div>
                    ))}
                  </div>
                ))}
              </div>
            )}

            {/* ── SENTIMENT TAB ────────────────────────────────────────────── */}
            {activeTab === "sentiment" && (
              <div>
                <div className="label" style={{ marginBottom: 16 }}>SENTIMENT ANALYSIS — MANAGEMENT & ANALYST TONE</div>
                {state.sentiment_signals.length === 0 ? (
                  <div style={{ color: "#2a3040", fontSize: 10 }}>No sentiment data yet.</div>
                ) : state.sentiment_signals.map((sig, i) => (
                  <div key={i} style={{ marginBottom: 20, paddingBottom: 20, borderBottom: "1px solid #1a2035" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                      <span style={{ color: "#6b7585", fontSize: 9, letterSpacing: "0.1em", width: 140 }}>{sig.source.replace(/_/g," ").toUpperCase()}</span>
                      <span className="pill" style={{ background: `${SENTIMENT_COLOR[sig.label]}20`, color: SENTIMENT_COLOR[sig.label] }}>{sig.label.toUpperCase()}</span>
                      <span style={{ marginLeft: "auto", color: SENTIMENT_COLOR[sig.label], fontWeight: 600, fontSize: 14 }}>
                        {sig.score > 0 ? "+" : ""}{sig.score.toFixed(2)}
                      </span>
                    </div>
                    <div style={{ height: 8, background: "#1a2035", borderRadius: 2, marginBottom: 10, position: "relative" }}>
                      <div style={{ position: "absolute", left: "50%", top: 0, width: 1, height: "100%", background: "#2a3040" }} />
                      <div style={{
                        position: "absolute", height: "100%", borderRadius: 2,
                        background: SENTIMENT_COLOR[sig.label],
                        left: sig.score >= 0 ? "50%" : `${(0.5 + sig.score / 2) * 100}%`,
                        width: `${Math.abs(sig.score) * 50}%`,
                      }} />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 8, color: "#2a3040" }}>
                      <span>BEARISH −1.0</span>
                      <span style={{ color: "#4a5568" }}>Confidence: {(sig.confidence * 100).toFixed(0)}%</span>
                      <span>BULLISH +1.0</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── HITL REVIEW TAB ──────────────────────────────────────────── */}
            {activeTab === "hitl" && (
              <div>
                <div className="label" style={{ marginBottom: 16 }}>HUMAN-IN-THE-LOOP REVIEW</div>
                {!state.hitl_required ? (
                  <div style={{ color: "#2a3040", fontSize: 10 }}>
                    {state.status === "complete" ? "Review completed." : "No human review required for this run."}
                  </div>
                ) : (
                  <div>
                    <div style={{ background: "#1a120a", border: "1px solid #8c4e00", borderRadius: 4, padding: "14px 16px", marginBottom: 20 }}>
                      <div style={{ color: "#f0a040", fontSize: 11, fontWeight: 500, marginBottom: 6 }}>REVIEW TRIGGERED</div>
                      <div style={{ color: "#8c6030", fontSize: 10, lineHeight: 1.8 }}>
                        Reason: Confidence score 0.68 is below the 0.80 threshold<br />
                        2 unverified claims flagged by FactChecker<br />
                        1 HIGH-severity regulatory risk identified
                      </div>
                    </div>

                    {/* Claims to Review */}
                    <div className="label" style={{ marginBottom: 10 }}>FLAGGED CLAIMS</div>
                    {["EU Digital Markets Act compliance burden estimated $2-4B annually based on regulatory filing analysis",
                      "EPS beat consensus by 3.1% — needs cross-check with FactSet data"].map((claim, i) => (
                      <div key={i} style={{ background: "#0d1117", border: "1px solid #1e2535", borderRadius: 3, padding: "10px 14px", marginBottom: 8, display: "flex", gap: 10, alignItems: "flex-start" }}>
                        <span style={{ color: "#f0c040", fontSize: 16, flexShrink: 0 }}>⚠</span>
                        <span style={{ color: "#8899aa", fontSize: 10, lineHeight: 1.6 }}>{claim}</span>
                      </div>
                    ))}

                    {/* Review Decision */}
                    <div className="label" style={{ marginBottom: 10, marginTop: 20 }}>REVIEWER DECISION</div>
                    <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
                      {["approved","rejected","revised"].map(d => (
                        <button key={d} onClick={() => setReviewForm(f => ({ ...f, decision: d }))}
                          style={{ flex: 1, padding: "8px 0", fontSize: 10, letterSpacing: "0.08em",
                            background: reviewForm.decision === d ? (d === "approved" ? "#1b4a2a" : d === "rejected" ? "#4a1b1b" : "#1a2a4a") : "#0d1117",
                            color: reviewForm.decision === d ? (d === "approved" ? "#4caf50" : d === "rejected" ? "#f44336" : "#3d7bd8") : "#4a5568",
                            border: `1px solid ${reviewForm.decision === d ? (d === "approved" ? "#2d7a3d" : d === "rejected" ? "#7a2d2d" : "#2d4a7a") : "#1e2535"}`,
                            borderRadius: 2 }}>
                          {d.toUpperCase()}
                        </button>
                      ))}
                    </div>

                    <div className="label" style={{ marginBottom: 6 }}>REVIEWER NOTES</div>
                    <textarea value={reviewForm.notes} onChange={e => setReviewForm(f => ({ ...f, notes: e.target.value }))}
                      placeholder="Add review notes, justification, or revision instructions..."
                      style={{ width: "100%", height: 80, resize: "vertical", marginBottom: 14 }} />

                    <button className={reviewForm.decision === "approved" ? "btn-success" : reviewForm.decision === "rejected" ? "btn-danger" : "btn-primary"}
                      style={{ width: "100%", padding: "10px 0", fontSize: 11, letterSpacing: "0.08em" }} onClick={submitHITL}>
                      SUBMIT REVIEW — {reviewForm.decision.toUpperCase()} ↗
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ── REPORT TAB ───────────────────────────────────────────────── */}
            {activeTab === "report" && (
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                  <div className="label" style={{ margin: 0 }}>INVESTMENT RESEARCH MEMO</div>
                  {state.final_report && (
                    <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                      <span className="pill" style={{ background: "#1b4a2a", color: "#4caf50" }}>HITL APPROVED</span>
                      <span className="pill" style={{ background: "#1a2035", color: "#6b7585" }}>CONF {((state.final_report.confidence_score || 0.91) * 100).toFixed(0)}%</span>
                    </div>
                  )}
                </div>
                {!state.final_report ? (
                  <div style={{ color: "#2a3040", fontSize: 10 }}>Report not yet generated. Complete the analysis and HITL review.</div>
                ) : (
                  <div style={{ background: "#0d1117", border: "1px solid #1a2035", borderRadius: 4, padding: "20px 24px" }}>
                    <div style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 11, lineHeight: 1.9, color: "#a8b4c4", whiteSpace: "pre-wrap" }}>
                      {memoExpanded ? MOCK_MEMO : MOCK_MEMO.slice(0, 800) + "..."}
                    </div>
                    <button className="btn-ghost" style={{ marginTop: 14, fontSize: 10 }} onClick={() => setMemoExpanded(e => !e)}>
                      {memoExpanded ? "COLLAPSE ↑" : "READ FULL MEMO ↓"}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ── AUDIT TRAIL TAB ──────────────────────────────────────────── */}
            {activeTab === "audit" && (
              <div>
                <div className="label" style={{ marginBottom: 16 }}>FULL AUDIT TRAIL — IMMUTABLE EVENT LOG</div>
                {state.activity_log.length === 0 ? (
                  <div style={{ color: "#2a3040", fontSize: 10 }}>No audit events yet.</div>
                ) : (
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid #1a2035" }}>
                        {["TIME","AGENT","ACTION"].map(h => (
                          <th key={h} style={{ padding: "4px 8px", color: "#2a3040", fontSize: 8, letterSpacing: "0.1em", textAlign: "left" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {state.activity_log.map((ev, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid #0d1117" }}>
                          <td style={{ padding: "6px 8px", color: "#2a3040", fontVariantNumeric: "tabular-nums" }}>{ev.ts}</td>
                          <td style={{ padding: "6px 8px" }}><span className="agent-badge">{ev.agent}</span></td>
                          <td style={{ padding: "6px 8px", color: "#8899aa", lineHeight: 1.5 }}>{ev.msg}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT PANEL: Market Data + Run History ───────────────────────── */}
        <div style={{ borderLeft: "1px solid #1a2035", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "14px 16px", borderBottom: "1px solid #1a2035" }}>
            <div className="label" style={{ marginBottom: 12 }}>MARKET SNAPSHOT</div>
            {[
              { ticker: "AAPL",  price: "227.48", chg: "+0.82%", pos: true },
              { ticker: "MSFT",  price: "415.32", chg: "+1.14%", pos: true },
              { ticker: "GOOG",  price: "195.21", chg: "-0.33%", pos: false },
              { ticker: "META",  price: "588.67", chg: "+2.01%", pos: true },
              { ticker: "AMZN",  price: "224.92", chg: "+0.55%", pos: true },
              { ticker: "NVDA",  price: "136.41", chg: "-1.82%", pos: false },
            ].map((s, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", marginBottom: 6, padding: "4px 0", borderBottom: "1px solid #0d1117" }}>
                <span style={{ width: 44, fontWeight: 600, color: "#c8cdd8", fontSize: 10 }}>{s.ticker}</span>
                <span style={{ flex: 1, textAlign: "right", fontFamily: "'IBM Plex Sans', sans-serif", color: "#e2e8f0", fontSize: 12, fontVariantNumeric: "tabular-nums" }}>${s.price}</span>
                <span style={{ width: 58, textAlign: "right", fontSize: 10, color: s.pos ? "#4caf50" : "#f44336" }}>{s.chg}</span>
              </div>
            ))}
          </div>

          <div style={{ padding: "14px 16px", borderBottom: "1px solid #1a2035", flex: 1, overflowY: "auto" }}>
            <div className="label" style={{ marginBottom: 12 }}>RECENT RUNS</div>
            {[
              { ticker: "AAPL", type: "EARNINGS", status: "complete",  conf: 91, time: "14:32" },
              { ticker: "MSFT", type: "DEEP DIVE", status: "complete",  conf: 87, time: "11:15" },
              { ticker: "GOOG", type: "RISK",      status: "review",    conf: 71, time: "09:44" },
              { ticker: "NVDA", type: "PEERS",     status: "complete",  conf: 83, time: "08:20" },
            ].map((r, i) => (
              <div key={i} style={{ marginBottom: 10, padding: "8px 10px", background: "#0d1117", border: "1px solid #1a2035", borderRadius: 3 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, color: "#c8cdd8", fontSize: 11 }}>{r.ticker}</span>
                  <span style={{ fontSize: 8, color: "#4a5568", letterSpacing: "0.08em" }}>{r.type}</span>
                  <span style={{ marginLeft: "auto", fontSize: 8, color: "#2a3040" }}>{r.time}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div className="bar-bg" style={{ flex: 1, height: 3 }}>
                    <div className="bar-fill" style={{ width: `${r.conf}%`, height: 3, background: r.conf >= 80 ? "#4caf50" : "#f0c040" }} />
                  </div>
                  <span style={{ fontSize: 9, color: r.conf >= 80 ? "#4caf50" : "#f0c040" }}>{r.conf}%</span>
                  <span className="pill" style={{ fontSize: 7, background: r.status === "complete" ? "#1b4a2a" : "#2a1a06", color: r.status === "complete" ? "#4caf50" : "#f0a040" }}>
                    {r.status === "complete" ? "✓" : "⚠"}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div style={{ padding: "12px 16px", background: "#060810", borderTop: "1px solid #1a2035" }}>
            <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
              <div className="metric-card" style={{ flex: 1, padding: "8px 10px" }}>
                <div className="label" style={{ fontSize: 8 }}>GRAPH ENGINE</div>
                <div style={{ color: "#4caf50", fontSize: 9 }}>LangGraph 0.2.28</div>
              </div>
              <div className="metric-card" style={{ flex: 1, padding: "8px 10px" }}>
                <div className="label" style={{ fontSize: 8 }}>LLM</div>
                <div style={{ color: "#4caf50", fontSize: 9 }}>claude-sonnet</div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <div className="metric-card" style={{ flex: 1, padding: "8px 10px" }}>
                <div className="label" style={{ fontSize: 8 }}>VECTOR DB</div>
                <div style={{ color: "#4caf50", fontSize: 9 }}>Pinecone</div>
              </div>
              <div className="metric-card" style={{ flex: 1, padding: "8px 10px" }}>
                <div className="label" style={{ fontSize: 8 }}>CHECKPOINTER</div>
                <div style={{ color: "#4caf50", fontSize: 9 }}>PostgreSQL</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const MOCK_MEMO = `INVESTMENT RESEARCH MEMO
══════════════════════════════════════════════
Apple Inc. (AAPL) — Q4 FY2024 Earnings Analysis
Generated: ${new Date().toLocaleDateString()} | Confidence: 91% | HITL: Approved
══════════════════════════════════════════════

EXECUTIVE SUMMARY

Apple delivered a solid Q4 FY2024 with revenue of $94.9B (+6.1% YoY), driven by Services growth of 14.2% and recovering iPhone demand in developed markets. EPS of $1.64 beat consensus of $1.59 by 3.1%. Operating margin expanded 80bps to 31.7%, reflecting ongoing cost discipline and favorable mix shift toward high-margin Services.

INVESTMENT THESIS: OUTPERFORM. The compounding Services flywheel, combined with the nascent AI integration roadmap (Apple Intelligence), positions AAPL for multiple expansion. Near-term headwinds from China exposure (18% of revenue) and EU regulatory pressure are manageable.

FINANCIAL ANALYSIS [Source: 10-K FY2024, p.42; Earnings Transcript Q4]

Revenue grew $5.5B YoY to $94.9B. iPhone remained the largest segment at $46.2B, recovering from the prior year's 2.8% decline. Services reached $24.2B with gross margins of 74.1% — the highest in company history — pulling blended margins higher. Mac revenue of $7.7B benefited from the M4 transition cycle.

Free cash flow of $26.8B represents 28.2% of revenue. The company returned $25.2B to shareholders via buybacks and dividends, reducing diluted share count by 2.1% YoY.

MANAGEMENT SENTIMENT [Source: Q4 Earnings Transcript]

CEO Tim Cook's opening commentary registered a bullish sentiment score of +0.71. Language was characterized by high-confidence signals ("record Services revenue," "accelerating momentum") with limited hedging. The Q&A section showed more measured tone (+0.12) as analysts probed China softness and AI monetization timelines.

Forward guidance of $124-126B for Q1 FY2025 implies 4.1-5.8% YoY growth — in line with consensus but showing characteristic Apple conservatism.

RISK ASSESSMENT [Source: 10-K Risk Factors; EU Regulatory Filings]

1. EU Digital Markets Act [HIGH] — Compliance with DMA's interoperability requirements and App Store reforms estimated to cost $2-4B annually. The EU's ongoing investigation into Apple Pay could impose additional remedies. [Source: 10-K p.18, EU Commission Filing Dec 2024]

2. China Revenue Concentration [MEDIUM] — Greater China represents 18% of FY2024 revenue ($37.3B). Huawei's domestic competition and geopolitical tensions create material downside risk to 10-15% of total revenue. [Source: 10-K Geographic Segment Data]

3. Supply Chain Concentration [MEDIUM] — TSMC 3nm node dependency for A-series and M-series chips creates single-point-of-failure risk. TSMC Arizona fab ramp mitigates long-term but adds near-term cost premium. [Source: Supplier Responsibility Report 2024]

PEER COMPARISON

vs. MSFT (32.1× P/E), GOOG (24.2×), META (26.8×): AAPL at 30.2× P/E trades at a premium to Alphabet but discount to Microsoft. Given Services margin trajectory, the premium appears defensible. AAPL ranks in the 78th percentile for operating margin among Mag-7 peers.

INVESTMENT CONCLUSION

AAPL offers a rare combination of defensive cash generation, secular Services growth, and an embedded AI optionality call via Apple Intelligence. Target price: $260 (12-month, DCF + comps). Key risk to thesis: China macro deterioration or DMA remedies exceeding current estimates.

Confidence Note: 91% — All revenue and EPS figures verified against 10-K filings and earnings release. Regulatory risk estimates sourced from EU Commission documents and company disclosures.`;
