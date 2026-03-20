"""
CapitalMind — Main LangGraph Investment Research Graph.

Implements a production multi-agent workflow with:
  - Parallel analysis branches (financial, sentiment, risk, peers)
  - Multi-modal extraction node
  - Fact-checking with citation verification
  - HITL interrupt() gate with configurable confidence threshold
  - PostgreSQL checkpointing for fault tolerance
  - Full audit trail at every node
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import structlog
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt, Send

from src.graph.state import GraphStage, HITLDecision, ResearchState
from src.agents.financial_analyst import FinancialAnalystAgent
from src.agents.sentiment_analyst import SentimentAnalystAgent
from src.agents.risk_assessor import RiskAssessorAgent
from src.agents.peer_comparator import PeerComparatorAgent
from src.agents.multimodal_analyst import MultimodalAnalystAgent
from src.agents.synthesizer import SynthesizerAgent
from src.agents.fact_checker import FactCheckerAgent
from src.ingestion.sec_edgar import SECEdgarClient
from src.ingestion.market_data import MarketDataClient
from src.retrieval.pinecone_store import PineconeVectorStore
from src.audit.trail import AuditLogger
from src.utils.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── LLM clients (module-level singletons) ────────────────────────────────────
# All models served locally via Ollama — no API keys required.

_primary_llm = ChatOllama(
    model=settings.primary_model,
    base_url=settings.ollama_base_url,
    temperature=0.1,
    num_predict=8192,
)

_vision_llm = ChatOllama(
    model=settings.vision_model,
    base_url=settings.ollama_base_url,
    temperature=0.1,
    num_predict=4096,
)

_embeddings = OllamaEmbeddings(
    model=settings.embedding_model,
    base_url=settings.ollama_base_url,
)

# ── Agent instances ──────────────────────────────────────────────────────────

_financial_agent   = FinancialAnalystAgent(_primary_llm)
_sentiment_agent   = SentimentAnalystAgent(_primary_llm)
_risk_agent        = RiskAssessorAgent(_primary_llm)
_peer_agent        = PeerComparatorAgent(_primary_llm)
_multimodal_agent  = MultimodalAnalystAgent(_vision_llm)
_synthesizer       = SynthesizerAgent(_primary_llm)
_fact_checker      = FactCheckerAgent(_primary_llm)
_sec_client        = SECEdgarClient()
_market_client     = MarketDataClient()
_vector_store      = PineconeVectorStore(_embeddings)
_audit             = AuditLogger()


# ═══════════════════════════════════════════════════════════════════════════════
# NODE IMPLEMENTATIONS
# Each node is an async function: (state) → dict (partial state update)
# ═══════════════════════════════════════════════════════════════════════════════

async def ingest_documents_node(state: ResearchState) -> dict:
    """
    Ingestion node: fetches SEC filings + market data snapshot.
    Uploads raw documents to S3 and records references.
    """
    t0 = datetime.now(timezone.utc)
    ticker = state["ticker"]

    log = logger.bind(node="ingest_documents", ticker=ticker, run_id=state["run_id"])
    log.info("Starting document ingestion")

    raw_docs = []
    errors = list(state.get("errors", []))
    data_freshness: dict[str, str] = {}

    # ── SEC filings (parallel fetch) ─────────────────────────────────────────
    try:
        filing_tasks = [
            _sec_client.fetch_latest("10-K", ticker),
            _sec_client.fetch_latest("10-Q", ticker),
            _sec_client.fetch_latest("8-K",  ticker, count=3),
            _sec_client.fetch_earnings_transcript(ticker),
        ]
        filing_results = await asyncio.gather(*filing_tasks, return_exceptions=True)

        for result in filing_results:
            if isinstance(result, Exception):
                errors.append({"stage": "ingestion", "error": str(result)})
                log.warning("Filing fetch failed", error=str(result))
            elif result:
                raw_docs.extend(result if isinstance(result, list) else [result])
                data_freshness[result[0]["document_type"] if isinstance(result, list) else result["document_type"]] = (
                    datetime.now(timezone.utc).isoformat()
                )

    except Exception as e:
        errors.append({"stage": "ingestion_sec", "error": str(e)})
        log.error("SEC ingestion failed", error=str(e))

    # ── Real-time market snapshot ────────────────────────────────────────────
    try:
        market_snapshot = await _market_client.get_snapshot(ticker)
        data_freshness["market_data"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        market_snapshot = None
        errors.append({"stage": "market_data", "error": str(e)})

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)

    audit_event = _audit.create_event(
        stage=GraphStage.INGESTION,
        agent="DocumentIngester",
        action="fetch_raw_documents",
        input_summary=f"ticker={ticker}",
        output_summary=f"fetched {len(raw_docs)} documents",
        duration_ms=duration_ms,
    )

    log.info("Ingestion complete", doc_count=len(raw_docs))

    return {
        "raw_documents": raw_docs,
        "market_data_snapshot": market_snapshot,
        "data_freshness": data_freshness,
        "current_stage": GraphStage.EXTRACTION,
        "completed_stages": state.get("completed_stages", []) + [GraphStage.INGESTION],
        "errors": errors,
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def extract_multimodal_node(state: ResearchState) -> dict:
    """
    Multi-modal extraction: processes PDFs for tables, charts, images.
    Uses vision LLM to interpret figures. Chunks text for vector indexing.
    """
    t0 = datetime.now(timezone.utc)
    log = logger.bind(node="extract_multimodal", run_id=state["run_id"])
    log.info("Starting multi-modal extraction")

    all_chunks = []
    all_tables = []
    all_figures = []
    chart_interpretations = []

    for raw_doc in state["raw_documents"]:
        try:
            extraction = await _multimodal_agent.extract(raw_doc)
            all_chunks.extend(extraction["chunks"])
            all_tables.extend(extraction["tables"])
            all_figures.extend(extraction["figures"])
            chart_interpretations.extend(extraction["chart_interpretations"])
        except Exception as e:
            log.warning("Extraction failed for doc", source=raw_doc.get("source"), error=str(e))

    # ── Index chunks into Pinecone ─────────────────────────────────────────
    if all_chunks:
        try:
            await _vector_store.upsert_chunks(
                chunks=all_chunks,
                namespace=state["ticker"],
            )
            log.info("Indexed chunks", count=len(all_chunks))
        except Exception as e:
            log.error("Vector indexing failed", error=str(e))

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    audit_event = _audit.create_event(
        stage=GraphStage.EXTRACTION,
        agent="MultimodalExtractor",
        action="extract_and_index",
        input_summary=f"{len(state['raw_documents'])} documents",
        output_summary=f"{len(all_chunks)} chunks, {len(all_tables)} tables, {len(all_figures)} figures",
        duration_ms=duration_ms,
    )

    return {
        "document_chunks": all_chunks,
        "extracted_tables": all_tables,
        "extracted_figures": all_figures,
        "chart_interpretations": chart_interpretations,
        "current_stage": GraphStage.PLANNING,
        "completed_stages": state.get("completed_stages", []) + [GraphStage.EXTRACTION],
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def plan_research_node(state: ResearchState) -> dict:
    """
    Planner node: determines which analyses to run based on
    research_type and available data. Retrieves relevant context.
    """
    t0 = datetime.now(timezone.utc)

    # ── Retrieve relevant context from vector store ────────────────────────
    queries = _build_retrieval_queries(state)
    retrieved = []
    for query in queries:
        results = await _vector_store.similarity_search(
            query=query,
            namespace=state["ticker"],
            top_k=settings.retrieval_top_k,
        )
        retrieved.extend(results)

    # Deduplicate
    seen = set()
    unique_retrieved = []
    for chunk in retrieved:
        if chunk["chunk_id"] not in seen:
            seen.add(chunk["chunk_id"])
            unique_retrieved.append(chunk)

    plan = {
        "run_financial_analysis": True,
        "run_sentiment_analysis": len([d for d in state["raw_documents"] if d.get("document_type") in ["earnings_transcript", "10-K"]]) > 0,
        "run_risk_assessment": True,
        "run_peer_comparison": state["research_type"] in ["peer_comparison", "full_deep_dive"],
        "analysis_focus": _determine_focus(state),
        "context_chunks_count": len(unique_retrieved),
    }

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    audit_event = _audit.create_event(
        stage=GraphStage.PLANNING,
        agent="ResearchPlanner",
        action="plan_and_retrieve",
        input_summary=f"research_type={state['research_type']}",
        output_summary=f"plan={plan}, retrieved={len(unique_retrieved)} chunks",
        duration_ms=duration_ms,
    )

    return {
        "research_plan": plan,
        "retrieved_context": unique_retrieved,
        "current_stage": GraphStage.ANALYSIS,
        "completed_stages": state.get("completed_stages", []) + [GraphStage.PLANNING],
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def financial_analysis_node(state: ResearchState) -> dict:
    """Computes financial ratios, EPS analysis, growth metrics."""
    t0 = datetime.now(timezone.utc)

    metrics = await _financial_agent.analyze(
        ticker=state["ticker"],
        context_chunks=state["retrieved_context"],
        extracted_tables=state["extracted_tables"],
        market_snapshot=state.get("market_data_snapshot"),
    )

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    audit_event = _audit.create_event(
        stage=GraphStage.ANALYSIS,
        agent="FinancialAnalyst",
        action="compute_metrics",
        input_summary=f"ticker={state['ticker']}",
        output_summary=f"revenue={metrics.get('revenue')}, margin={metrics.get('operating_margin')}",
        duration_ms=duration_ms,
        token_usage=getattr(metrics, "_token_usage", {}),
    )

    return {
        "financial_metrics": metrics,
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def sentiment_analysis_node(state: ResearchState) -> dict:
    """Analyzes management tone, analyst sentiment, and forward guidance."""
    t0 = datetime.now(timezone.utc)

    signals = await _sentiment_agent.analyze(
        ticker=state["ticker"],
        context_chunks=state["retrieved_context"],
        document_types=["earnings_transcript", "10-K", "8-K"],
    )

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    audit_event = _audit.create_event(
        stage=GraphStage.ANALYSIS,
        agent="SentimentAnalyst",
        action="analyze_sentiment",
        input_summary=f"ticker={state['ticker']}",
        output_summary=f"{len(signals)} signals extracted",
        duration_ms=duration_ms,
    )

    return {
        "sentiment_signals": signals,
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def risk_assessment_node(state: ResearchState) -> dict:
    """Identifies and categorizes risk factors from filings and news."""
    t0 = datetime.now(timezone.utc)

    flags = await _risk_agent.assess(
        ticker=state["ticker"],
        context_chunks=state["retrieved_context"],
        financial_metrics=state.get("financial_metrics"),
    )

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    audit_event = _audit.create_event(
        stage=GraphStage.ANALYSIS,
        agent="RiskAssessor",
        action="identify_risk_flags",
        input_summary=f"ticker={state['ticker']}",
        output_summary=f"{len(flags)} flags: {[f['severity'] for f in flags]}",
        duration_ms=duration_ms,
    )

    return {
        "risk_flags": flags,
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def peer_comparison_node(state: ResearchState) -> dict:
    """Benchmarks against sector peers. Only runs if plan calls for it."""
    if not state.get("research_plan", {}).get("run_peer_comparison"):
        return {"peer_comparison": None}

    t0 = datetime.now(timezone.utc)
    comparison = await _peer_agent.compare(
        ticker=state["ticker"],
        financial_metrics=state.get("financial_metrics"),
    )

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    audit_event = _audit.create_event(
        stage=GraphStage.ANALYSIS,
        agent="PeerComparator",
        action="benchmark_peers",
        input_summary=f"ticker={state['ticker']}",
        output_summary=f"peers={comparison.get('peers', [])}",
        duration_ms=duration_ms,
    )

    return {
        "peer_comparison": comparison,
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def synthesize_node(state: ResearchState) -> dict:
    """
    Synthesizer: combines all analysis outputs into a structured
    investment research memo with inline citations.
    """
    t0 = datetime.now(timezone.utc)
    log = logger.bind(node="synthesize", run_id=state["run_id"])
    log.info("Synthesizing research memo")

    draft, overall_confidence = await _synthesizer.synthesize(
        ticker=state["ticker"],
        company_name=state["company_name"],
        research_type=state["research_type"],
        financial_metrics=state.get("financial_metrics"),
        sentiment_signals=state.get("sentiment_signals", []),
        risk_flags=state.get("risk_flags", []),
        peer_comparison=state.get("peer_comparison"),
        retrieved_context=state.get("retrieved_context", []),
        chart_interpretations=state.get("chart_interpretations", []),
        extracted_tables=state.get("extracted_tables", []),
        market_snapshot=state.get("market_data_snapshot"),
    )

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    audit_event = _audit.create_event(
        stage=GraphStage.SYNTHESIS,
        agent="Synthesizer",
        action="generate_draft_memo",
        input_summary=f"ticker={state['ticker']}, analyses_combined=4",
        output_summary=f"draft_length={len(draft)}, confidence={overall_confidence:.2f}",
        duration_ms=duration_ms,
    )

    return {
        "draft_memo": draft,
        "overall_confidence": overall_confidence,
        "current_stage": GraphStage.FACT_CHECK,
        "completed_stages": state.get("completed_stages", []) + [GraphStage.SYNTHESIS],
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def fact_check_node(state: ResearchState) -> dict:
    """
    Fact-checker: validates every claim in the memo against
    source documents. Flags unverified or contradicted claims.
    """
    t0 = datetime.now(timezone.utc)

    cited_claims = await _fact_checker.verify(
        draft_memo=state["draft_memo"],
        context_chunks=state["retrieved_context"],
        ticker=state["ticker"],
    )

    # Recompute confidence after fact-checking
    verified_ratio = sum(1 for c in cited_claims if c["verified"]) / max(len(cited_claims), 1)
    avg_claim_confidence = sum(c["confidence"] for c in cited_claims) / max(len(cited_claims), 1)
    adjusted_confidence = (state["overall_confidence"] * 0.4 + verified_ratio * 0.4 + avg_claim_confidence * 0.2)

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    audit_event = _audit.create_event(
        stage=GraphStage.FACT_CHECK,
        agent="FactChecker",
        action="verify_claims",
        input_summary=f"draft_memo_claims_extracted={len(cited_claims)}",
        output_summary=f"verified={verified_ratio:.0%}, adjusted_confidence={adjusted_confidence:.2f}",
        duration_ms=duration_ms,
    )

    return {
        "cited_claims": cited_claims,
        "overall_confidence": adjusted_confidence,
        "current_stage": GraphStage.HITL_REVIEW,
        "completed_stages": state.get("completed_stages", []) + [GraphStage.FACT_CHECK],
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def hitl_router_node(state: ResearchState) -> dict:
    """
    Determines whether human review is required.
    Triggers interrupt() if confidence < threshold or critical risks found.
    """
    confidence = state.get("overall_confidence", 0.0)
    critical_risks = [f for f in state.get("risk_flags", []) if f["severity"] == "critical"]
    unverified_claims = [c for c in state.get("cited_claims", []) if not c["verified"]]

    needs_hitl = (
        confidence < settings.hitl_confidence_threshold
        or len(critical_risks) > 0
        or len(unverified_claims) > 2
    )

    if not needs_hitl:
        return {
            "hitl_required": False,
            "current_stage": GraphStage.REPORT,
        }

    # ── Trigger LangGraph interrupt() — pauses graph for human input ────────
    reasons = []
    if confidence < settings.hitl_confidence_threshold:
        reasons.append(f"Low confidence score: {confidence:.2f}")
    if critical_risks:
        reasons.append(f"{len(critical_risks)} critical risk flags detected")
    if unverified_claims:
        reasons.append(f"{len(unverified_claims)} unverified claims in memo")

    review_packet: dict = {
        "review_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": "; ".join(reasons),
        "confidence_score": confidence,
        "sections_flagged": [c["claim"][:100] for c in unverified_claims[:5]],
        "reviewer_id": None,
        "decision": HITLDecision.PENDING,
        "reviewer_notes": None,
        "revised_sections": None,
        "reviewed_at": None,
    }

    # LangGraph interrupt() — graph serializes state and waits.
    # The FastAPI /review endpoint resumes with human decision.
    human_decision: dict = interrupt({
        "type": "human_review_required",
        "review_packet": review_packet,
        "draft_memo_preview": state["draft_memo"][:2000],
        "risk_flags": state.get("risk_flags", []),
        "confidence": confidence,
    })

    # ── Resume after human input ─────────────────────────────────────────────
    review_packet["decision"] = human_decision.get("decision", HITLDecision.APPROVED)
    review_packet["reviewer_id"] = human_decision.get("reviewer_id")
    review_packet["reviewer_notes"] = human_decision.get("notes")
    review_packet["revised_sections"] = human_decision.get("revised_sections")
    review_packet["reviewed_at"] = datetime.now(timezone.utc).isoformat()

    audit_event = _audit.create_event(
        stage=GraphStage.HITL_REVIEW,
        agent="HITLGateway",
        action="human_review_completed",
        input_summary=f"reason={'; '.join(reasons)}",
        output_summary=f"decision={review_packet['decision']}, reviewer={review_packet['reviewer_id']}",
        duration_ms=0,
        metadata={"review_id": review_packet["review_id"]},
    )

    next_stage = (
        GraphStage.REPORT
        if review_packet["decision"] in [HITLDecision.APPROVED, HITLDecision.REVISED]
        else GraphStage.ERROR
    )

    return {
        "hitl_required": True,
        "hitl_packet": review_packet,
        "current_stage": next_stage,
        "completed_stages": state.get("completed_stages", []) + [GraphStage.HITL_REVIEW],
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


async def generate_report_node(state: ResearchState) -> dict:
    """
    Final report assembly. Applies any HITL revisions,
    structures the memo, and uploads to S3.
    """
    t0 = datetime.now(timezone.utc)

    memo = state["draft_memo"]

    # Apply HITL revisions if any
    if state.get("hitl_packet") and state["hitl_packet"].get("revised_sections"):
        for section, revised_text in state["hitl_packet"]["revised_sections"].items():
            memo = memo.replace(f"[SECTION:{section}]", revised_text)

    final_report = {
        "report_id": state["run_id"],
        "ticker": state["ticker"],
        "company_name": state["company_name"],
        "research_type": state["research_type"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": state["requested_by"],
        "confidence_score": state["overall_confidence"],
        "memo": memo,
        "financial_metrics": state.get("financial_metrics"),
        "sentiment_summary": _summarize_sentiment(state.get("sentiment_signals", [])),
        "risk_summary": state.get("risk_flags", []),
        "peer_comparison": state.get("peer_comparison"),
        "cited_claims": state.get("cited_claims", []),
        "hitl_reviewed": state.get("hitl_required", False),
        "hitl_reviewer": state.get("hitl_packet", {}).get("reviewer_id") if state.get("hitl_packet") else None,
        "data_freshness": state.get("data_freshness", {}),
        "sources": _collect_sources(state),
        "audit_summary": {
            "total_events": len(state.get("audit_trail", [])),
            "stages_completed": state.get("completed_stages", []),
            "errors": state.get("errors", []),
        },
    }

    # Upload to S3
    s3_uri = None
    try:
        from src.utils.s3 import upload_report
        s3_uri = await upload_report(final_report, state["ticker"], state["run_id"])
    except Exception as e:
        logger.warning("S3 upload failed", error=str(e))

    duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    audit_event = _audit.create_event(
        stage=GraphStage.REPORT,
        agent="ReportGenerator",
        action="generate_final_report",
        input_summary=f"ticker={state['ticker']}, hitl={state.get('hitl_required')}",
        output_summary=f"report_id={state['run_id']}, s3_uri={s3_uri}",
        duration_ms=duration_ms,
    )

    return {
        "final_report": final_report,
        "report_s3_uri": s3_uri,
        "current_stage": GraphStage.COMPLETE,
        "completed_stages": state.get("completed_stages", []) + [GraphStage.REPORT],
        "audit_trail": state.get("audit_trail", []) + [audit_event],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING FUNCTIONS (conditional edges)
# ═══════════════════════════════════════════════════════════════════════════════

def route_after_hitl(state: ResearchState) -> Literal["generate_report", "__end__"]:
    """Route based on HITL decision."""
    if state.get("hitl_packet"):
        decision = state["hitl_packet"].get("decision")
        if decision == HITLDecision.REJECTED:
            return END
    return "generate_report"


def route_parallel_analyses(state: ResearchState) -> list[Send]:
    """
    Fan-out: send parallel messages to all analysis nodes.
    LangGraph's Send API enables true parallel execution.
    """
    plan = state.get("research_plan", {})
    sends = [
        Send("financial_analysis", state),
        Send("sentiment_analysis", state),
        Send("risk_assessment", state),
    ]
    if plan.get("run_peer_comparison"):
        sends.append(Send("peer_comparison", state))
    return sends


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_graph(checkpointer=None) -> StateGraph:
    """
    Constructs and compiles the full investment research graph.

    Graph topology:
        START
          → ingest_documents
          → extract_multimodal
          → plan_research
          → [parallel fan-out via Send]:
              → financial_analysis ─┐
              → sentiment_analysis  ├── (join) → synthesize
              → risk_assessment   ──┤
              → peer_comparison ────┘
          → fact_check
          → hitl_router
          → [conditional]: generate_report | END
          → END
    """
    builder = StateGraph(ResearchState)

    # ── Add nodes ────────────────────────────────────────────────────────────
    builder.add_node("ingest_documents",   ingest_documents_node)
    builder.add_node("extract_multimodal", extract_multimodal_node)
    builder.add_node("plan_research",      plan_research_node)
    builder.add_node("financial_analysis", financial_analysis_node)
    builder.add_node("sentiment_analysis", sentiment_analysis_node)
    builder.add_node("risk_assessment",    risk_assessment_node)
    builder.add_node("peer_comparison",    peer_comparison_node)
    builder.add_node("synthesize",         synthesize_node)
    builder.add_node("fact_check",         fact_check_node)
    builder.add_node("hitl_router",        hitl_router_node)
    builder.add_node("generate_report",    generate_report_node)

    # ── Sequential edges ─────────────────────────────────────────────────────
    builder.add_edge(START,                "ingest_documents")
    builder.add_edge("ingest_documents",   "extract_multimodal")
    builder.add_edge("extract_multimodal", "plan_research")

    # ── Parallel fan-out from plan_research ──────────────────────────────────
    builder.add_conditional_edges(
        "plan_research",
        route_parallel_analyses,
        ["financial_analysis", "sentiment_analysis", "risk_assessment", "peer_comparison"],
    )

    # ── Join: all analyses → synthesize ──────────────────────────────────────
    builder.add_edge("financial_analysis", "synthesize")
    builder.add_edge("sentiment_analysis", "synthesize")
    builder.add_edge("risk_assessment",    "synthesize")
    builder.add_edge("peer_comparison",    "synthesize")

    # ── Synthesis → fact-check → HITL ────────────────────────────────────────
    builder.add_edge("synthesize",   "fact_check")
    builder.add_edge("fact_check",   "hitl_router")

    # ── Conditional after HITL ───────────────────────────────────────────────
    builder.add_conditional_edges(
        "hitl_router",
        route_after_hitl,
        {"generate_report": "generate_report", "__end__": END},
    )

    builder.add_edge("generate_report", END)

    return builder.compile(checkpointer=checkpointer)


async def create_production_graph():
    """
    Factory that builds graph with PostgreSQL checkpointer.
    Used in production API. The checkpointer enables:
      - Fault tolerance (resume after crash)
      - HITL pause/resume across HTTP requests
      - Full state history for audit
    """
    from src.utils.settings import get_settings
    settings = get_settings()

    conn_str = settings.database_url.replace("+asyncpg", "")

    try:
        from psycopg_pool import AsyncConnectionPool
        
        # We need a persistent connection pool for the checkpointer
        global _pg_pool
        _pg_pool = AsyncConnectionPool(conninfo=conn_str, max_size=10, open=False)
        await _pg_pool.open()
        
        checkpointer = AsyncPostgresSaver(_pg_pool)
        await checkpointer.setup()
        
        return build_graph(checkpointer=checkpointer)
    except Exception as e:
        import structlog
        structlog.get_logger().warning(
            "Could not connect to PostgreSQL checkpointer. Falling back to MemorySaver.", 
            error=str(e)
        )
        from langgraph.checkpoint.memory import MemorySaver
        return build_graph(checkpointer=MemorySaver())


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_retrieval_queries(state: ResearchState) -> list[str]:
    ticker = state["ticker"]
    company = state["company_name"]
    return [
        f"{company} revenue earnings financial performance",
        f"{ticker} risk factors regulatory compliance",
        f"{company} management guidance outlook future",
        f"{ticker} cash flow debt balance sheet",
        f"{company} competitive position market share",
    ]


def _determine_focus(state: ResearchState) -> str:
    rt = state["research_type"]
    focus_map = {
        "earnings_analysis":  "earnings performance vs expectations",
        "peer_comparison":    "relative valuation and competitive positioning",
        "risk_assessment":    "material risk identification and quantification",
        "full_deep_dive":     "comprehensive investment thesis",
        "quick_summary":      "key highlights and investment takeaways",
    }
    return focus_map.get(rt, "comprehensive analysis")


def _summarize_sentiment(signals: list) -> dict:
    if not signals:
        return {"overall": "neutral", "score": 0.0}
    avg = sum(s["score"] for s in signals) / len(signals)
    label = "bullish" if avg > 0.2 else "bearish" if avg < -0.2 else "neutral"
    return {"overall": label, "score": round(avg, 3), "signals": len(signals)}


def _collect_sources(state: ResearchState) -> list[str]:
    sources = set()
    for doc in state.get("raw_documents", []):
        sources.add(f"{doc.get('document_type', 'unknown')} — {doc.get('filing_date', 'N/A')}")
    return sorted(sources)
