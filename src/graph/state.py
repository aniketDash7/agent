"""
CapitalMind — Shared LangGraph State.

This TypedDict is passed between every node in the graph.
It is the single source of truth for all agent data, annotations,
audit events, and HITL decision points.
"""
from __future__ import annotations

from typing import Annotated, Any, TypedDict, Sequence
from enum import Enum
from datetime import datetime
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# ── Enums ────────────────────────────────────────────────────────────────────

class ResearchType(str, Enum):
    EARNINGS_ANALYSIS  = "earnings_analysis"
    PEER_COMPARISON    = "peer_comparison"
    RISK_ASSESSMENT    = "risk_assessment"
    FULL_DEEP_DIVE     = "full_deep_dive"
    QUICK_SUMMARY      = "quick_summary"


class DocumentType(str, Enum):
    SEC_10K   = "10-K"
    SEC_10Q   = "10-Q"
    SEC_8K    = "8-K"
    TRANSCRIPT = "earnings_transcript"
    ANALYST    = "analyst_report"
    NEWS       = "news_article"
    MARKET     = "market_data"


class HITLDecision(str, Enum):
    APPROVED  = "approved"
    REJECTED  = "rejected"
    REVISED   = "revised"
    PENDING   = "pending"


class GraphStage(str, Enum):
    INGESTION     = "ingestion"
    EXTRACTION    = "extraction"
    PLANNING      = "planning"
    ANALYSIS      = "analysis"
    SYNTHESIS     = "synthesis"
    FACT_CHECK    = "fact_check"
    HITL_REVIEW   = "hitl_review"
    REPORT        = "report"
    COMPLETE      = "complete"
    ERROR         = "error"


# ── Sub-schemas (plain dicts for serializability) ─────────────────────────────

class DocumentChunk(TypedDict):
    chunk_id: str
    source_id: str
    document_type: str
    ticker: str
    text: str
    metadata: dict[str, Any]          # page, table_index, figure_index, etc.
    embedding_id: str | None
    extracted_tables: list[dict]       # Structured table data
    extracted_figures: list[dict]      # Chart descriptions from vision LLM


class FinancialMetrics(TypedDict):
    ticker: str
    period: str
    revenue: float | None
    gross_margin: float | None
    operating_margin: float | None
    net_margin: float | None
    eps: float | None
    eps_beat: float | None            # Beat vs estimate (%)
    revenue_growth_yoy: float | None
    fcf: float | None
    debt_to_equity: float | None
    current_ratio: float | None
    roe: float | None
    pe_ratio: float | None
    ev_ebitda: float | None
    raw: dict[str, Any]               # Full raw data


class SentimentSignal(TypedDict):
    source: str                        # "management", "analyst", "news"
    score: float                       # -1.0 to 1.0
    label: str                         # "bullish" | "bearish" | "neutral"
    confidence: float
    key_phrases: list[str]
    tone_indicators: list[str]         # hedging, confidence, uncertainty markers
    forward_guidance: str | None


class RiskFlag(TypedDict):
    category: str          # "regulatory", "market", "operational", "ESG", "liquidity"
    severity: str          # "critical", "high", "medium", "low"
    description: str
    evidence: list[str]    # Cited passages
    sources: list[str]


class PeerComparison(TypedDict):
    ticker: str
    peers: list[str]
    sector: str
    metrics_vs_peers: dict[str, Any]   # metric → {company, peer_avg, percentile}
    competitive_position: str
    moat_assessment: str


class CitedClaim(TypedDict):
    claim: str
    verified: bool
    confidence: float
    supporting_sources: list[str]
    contradicting_sources: list[str]
    verifier_notes: str


class AuditEvent(TypedDict):
    event_id: str
    timestamp: str
    stage: str
    agent: str
    action: str
    input_summary: str
    output_summary: str
    duration_ms: int
    model_used: str
    token_usage: dict[str, int]
    metadata: dict[str, Any]


class HITLReviewPacket(TypedDict):
    review_id: str
    created_at: str
    reason: str                      # Why HITL was triggered
    confidence_score: float
    sections_flagged: list[str]
    reviewer_id: str | None
    decision: str                    # HITLDecision enum value
    reviewer_notes: str | None
    revised_sections: dict[str, str] | None
    reviewed_at: str | None


# ── Main Graph State ─────────────────────────────────────────────────────────

class ResearchState(TypedDict):
    # ── Request context ─────────────────────────────────────────────────────
    run_id: str
    ticker: str
    company_name: str
    research_type: str                      # ResearchType enum value
    requested_by: str
    created_at: str

    # ── LangGraph message history (append-only via add_messages) ────────────
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # ── Pipeline stage tracking ──────────────────────────────────────────────
    current_stage: str                      # GraphStage enum value
    completed_stages: list[str]
    errors: list[dict[str, str]]

    # ── Ingested raw documents ───────────────────────────────────────────────
    raw_documents: list[dict[str, Any]]     # S3 references + metadata
    document_chunks: list[DocumentChunk]
    retrieved_context: list[DocumentChunk]  # From vector search

    # ── Analysis outputs ─────────────────────────────────────────────────────
    financial_metrics: FinancialMetrics | None
    sentiment_signals: list[SentimentSignal]
    risk_flags: list[RiskFlag]
    peer_comparison: PeerComparison | None

    # ── Multi-modal extractions ──────────────────────────────────────────────
    extracted_tables: list[dict[str, Any]]
    extracted_figures: list[dict[str, Any]]
    chart_interpretations: list[str]

    # ── Synthesis ────────────────────────────────────────────────────────────
    research_plan: dict[str, Any]           # Planner output
    draft_memo: str
    cited_claims: list[CitedClaim]
    overall_confidence: float

    # ── Human-in-the-loop ────────────────────────────────────────────────────
    hitl_required: bool
    hitl_packet: HITLReviewPacket | None

    # ── Final output ─────────────────────────────────────────────────────────
    final_report: dict[str, Any] | None
    report_s3_uri: str | None

    # ── Audit trail (append-only list) ──────────────────────────────────────
    audit_trail: list[AuditEvent]

    # ── Real-time metadata ───────────────────────────────────────────────────
    market_data_snapshot: dict[str, Any] | None
    data_freshness: dict[str, str]          # source → last_updated ISO timestamp
