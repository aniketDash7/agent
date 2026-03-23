"""
CapitalMind — FastAPI Application
Production-grade async API with WebSocket support for real-time
agent activity streaming, HITL review endpoints, and audit trail access.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.graph.investment_graph import create_production_graph
from src.graph.state import ResearchType
from src.audit.trail import AuditPersister
from src.utils.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# ── App state ─────────────────────────────────────────────────────────────────
_graph = None
_audit = AuditPersister()
_ws_connections: dict[str, list[WebSocket]] = {}  # run_id → [ws]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global _graph
    logger.info("CapitalMind starting up", env=settings.app_env)

    # Initialize database tables
    try:
        await _audit.initialize()
        logger.info("Audit tables ready")
    except Exception as e:
        logger.warning("Audit init failed", error=str(e))

    # Build LangGraph with PostgreSQL checkpointer
    try:
        _graph = await create_production_graph()
        logger.info("LangGraph compiled and ready")
    except Exception as e:
        logger.error("Graph init failed", error=str(e))
        _graph = None

    yield

    logger.info("CapitalMind shutting down")


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="CapitalMind",
    description="AI-Powered Investment Research Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, pattern="^[A-Z]{1,5}$")
    company_name: str = Field(default="")
    research_type: str = Field(default=ResearchType.EARNINGS_ANALYSIS)
    requested_by: str = Field(default="api_user")

    model_config = {"json_schema_extra": {"example": {
        "ticker": "AAPL", "company_name": "Apple Inc.",
        "research_type": "earnings_analysis", "requested_by": "analyst@firm.com"
    }}}


class HITLReviewRequest(BaseModel):
    run_id: str
    decision: str = Field(..., pattern="^(approved|rejected|revised)$")
    reviewer_id: str
    notes: str = ""
    revised_sections: dict[str, str] | None = None


class ResearchRunResponse(BaseModel):
    run_id: str
    status: str
    ticker: str
    message: str


# ── API Routes ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "graph_ready": _graph is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@app.post("/api/research", response_model=ResearchRunResponse)
async def start_research(req: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Start an asynchronous investment research run.
    Returns immediately with run_id. Subscribe to WebSocket for updates.
    """
    if not _graph:
        raise HTTPException(503, "Research graph not initialized")

    run_id = str(uuid.uuid4())
    ticker = req.ticker.upper()
    company_name = req.company_name or ticker

    # Register run in audit DB
    await _audit.persist_run(
        run_id=run_id, ticker=ticker, company_name=company_name,
        research_type=req.research_type, requested_by=req.requested_by,
    )

    # Initial state
    initial_state = {
        "run_id": run_id,
        "ticker": ticker,
        "company_name": company_name,
        "research_type": req.research_type,
        "requested_by": req.requested_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],
        "current_stage": "ingestion",
        "completed_stages": [],
        "errors": [],
        "raw_documents": [],
        "document_chunks": [],
        "retrieved_context": [],
        "financial_metrics": None,
        "sentiment_signals": [],
        "risk_flags": [],
        "peer_comparison": None,
        "extracted_tables": [],
        "extracted_figures": [],
        "chart_interpretations": [],
        "research_plan": {},
        "draft_memo": "",
        "cited_claims": [],
        "overall_confidence": 0.0,
        "hitl_required": False,
        "hitl_packet": None,
        "final_report": None,
        "report_s3_uri": None,
        "audit_trail": [],
        "market_data_snapshot": None,
        "data_freshness": {},
    }

    # Run graph in background
    background_tasks.add_task(
        _run_graph_background, run_id, ticker, initial_state
    )

    logger.info("Research run started", run_id=run_id, ticker=ticker)

    return ResearchRunResponse(
        run_id=run_id,
        status="running",
        ticker=ticker,
        message=f"Research started. Connect to /ws/{run_id} for live updates.",
    )


@app.get("/api/research/{run_id}")
async def get_research_result(run_id: str):
    """Get the current state / final report for a run."""
    if not _graph:
        raise HTTPException(503, "Graph not initialized")

    try:
        config = {"configurable": {"thread_id": run_id}}
        state = await _graph.aget_state(config)
        if not state or not state.values:
            raise HTTPException(404, f"Run {run_id} not found")

        values = state.values
        return {
            "run_id": run_id,
            "status": _get_run_status(values),
            "current_stage": values.get("current_stage"),
            "completed_stages": values.get("completed_stages", []),
            "ticker": values.get("ticker"),
            "final_report": values.get("final_report"),
            "overall_confidence": values.get("overall_confidence"),
            "hitl_required": values.get("hitl_required"),
            "hitl_packet": values.get("hitl_packet"),
            "financial_metrics": values.get("financial_metrics"),
            "sentiment_signals": values.get("sentiment_signals", []),
            "risk_flags": values.get("risk_flags", []),
            "errors": values.get("errors", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/research/{run_id}/review")
async def submit_hitl_review(run_id: str, review: HITLReviewRequest):
    """
    Submit a human review decision to resume a paused LangGraph run.
    This is how HITL works: the graph pauses at interrupt(), the reviewer
    submits their decision here, and we resume with Command(resume=...).
    """
    if not _graph:
        raise HTTPException(503, "Graph not initialized")

    from langgraph.types import Command

    config = {"configurable": {"thread_id": run_id}}

    try:
        # Resume graph with human decision
        resume_value = {
            "decision": review.decision,
            "reviewer_id": review.reviewer_id,
            "notes": review.notes,
            "revised_sections": review.revised_sections,
        }
        await _graph.aupdate_state(config, {}, as_node="hitl_router")
        result = await _graph.ainvoke(
            Command(resume=resume_value), config=config
        )

        # Persist audit events
        if result.get("audit_trail"):
            await _audit.persist_events(
                run_id, result.get("ticker",""), result["audit_trail"]
            )

        return {"run_id": run_id, "decision": review.decision, "status": "resumed"}

    except Exception as e:
        logger.error("HITL resume failed", run_id=run_id, error=str(e))
        raise HTTPException(500, str(e))


@app.get("/api/audit/{run_id}")
async def get_audit_trail(run_id: str):
    """Full audit trail for a research run."""
    events = await _audit.get_run_audit(run_id)
    return {"run_id": run_id, "events": events, "total": len(events)}


@app.get("/api/runs")
async def get_recent_runs(ticker: str | None = None, limit: int = 20):
    """Get recent research runs."""
    runs = await _audit.get_recent_runs(ticker=ticker, limit=limit)
    return {"runs": runs, "total": len(runs)}


# ── WebSocket: Real-time Agent Activity ──────────────────────────────────────

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """
    WebSocket endpoint for real-time agent activity streaming.
    Clients connect here to receive live updates as the graph executes.
    """
    await websocket.accept()
    _ws_connections.setdefault(run_id, []).append(websocket)

    try:
        while True:
            # Keep connection alive; server pushes events
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        _ws_connections.get(run_id, []).remove(websocket)


async def _broadcast_to_run(run_id: str, message: dict):
    """Push a message to all WebSocket clients watching a run."""
    connections = _ws_connections.get(run_id, [])
    dead = []
    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.remove(ws)


# ── Background Graph Runner ───────────────────────────────────────────────────

async def _run_graph_background(run_id: str, ticker: str, initial_state: dict):
    """Execute the LangGraph in background, streaming events to WebSocket."""
    config = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": 50,
    }

    try:
        # Stream events for real-time WebSocket updates
        async for event in _graph.astream_events(initial_state, config, version="v2"):
            event_name = event.get("name", "")
            event_kind = event.get("event", "")

            if event_kind == "on_chain_start" and event_name not in ("LangGraph",):
                await _broadcast_to_run(run_id, {
                    "type": "agent_start",
                    "agent": event_name,
                    "run_id": run_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif event_kind == "on_chain_end" and event_name not in ("LangGraph",):
                output = event.get("data", {}).get("output", {})
                current_stage = output.get("current_stage", "") if isinstance(output, dict) else ""
                await _broadcast_to_run(run_id, {
                    "type": "agent_complete",
                    "agent": event_name,
                    "stage": current_stage,
                    "run_id": run_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        # Get final state
        final_config = {"configurable": {"thread_id": run_id}}
        final_state_snapshot = await _graph.aget_state(final_config)
        final_values = final_state_snapshot.values if final_state_snapshot else {}

        # Check if HITL interrupt occurred
        if final_state_snapshot and final_state_snapshot.next:
            await _broadcast_to_run(run_id, {
                "type": "hitl_required",
                "run_id": run_id,
                "hitl_packet": final_values.get("hitl_packet"),
                "confidence": final_values.get("overall_confidence"),
            })
        else:
            # Persist audit events and complete
            if final_values.get("audit_trail"):
                await _audit.persist_events(run_id, ticker, final_values["audit_trail"])

            await _audit.complete_run(
                run_id=run_id,
                status="complete",
                confidence=final_values.get("overall_confidence", 0.0),
                report_s3_uri=final_values.get("report_s3_uri"),
                hitl_required=final_values.get("hitl_required", False),
            )

            await _broadcast_to_run(run_id, {
                "type": "complete",
                "run_id": run_id,
                "confidence": final_values.get("overall_confidence"),
                "report": final_values.get("final_report"),
            })

    except Exception as e:
        logger.error("Graph execution failed", run_id=run_id, error=str(e))
        await _broadcast_to_run(run_id, {
            "type": "error",
            "run_id": run_id,
            "error": str(e),
        })
        try:
            await _audit.complete_run(run_id, "failed", 0.0, None, False)
        except Exception:
            pass


def _get_run_status(values: dict) -> str:
    stage = values.get("current_stage", "")
    if stage == "complete":
        return "complete"
    if values.get("hitl_required") and not values.get("hitl_packet", {}).get("reviewed_at"):
        return "awaiting_review"
    if values.get("errors"):
        return "error"
    return "running"


# ── Serve React Frontend ───────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="frontend/dist", check_dir=False), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("frontend/dist/index.html")
