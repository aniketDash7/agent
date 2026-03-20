"""
CapitalMind — Model Context Protocol (MCP) Server.
Exposes CapitalMind research capabilities to local AI clients (like Claude Desktop).
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
import structlog

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from src.graph.investment_graph import create_production_graph
from src.audit.trail import AuditPersister
from src.ingestion.market_data import MarketDataClient

app = Server("capitalmind")
logger = structlog.get_logger("mcp_server")

# Global state
_graph = None
_audit = AuditPersister()
_market_client = MarketDataClient()

async def ensure_initialized():
    """Ensure DB and Graph are initialized."""
    global _graph
    if _graph is None:
        await _audit.initialize()
        _graph = await create_production_graph()

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """Expose CapitalMind tools to the MCP client."""
    return [
        types.Tool(
            name="get_market_snapshot",
            description="Fetch a real-time market snapshot for a given stock ticker including price, volume, market cap, and valuation multiples.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "The stock ticker symbol (e.g., AAPL)"}
                },
                "required": ["ticker"]
            }
        ),
        types.Tool(
            name="run_investment_research",
            description="Run a full multi-agent investment research analysis on a stock ticker using CapitalMind. Returns a comprehensive markdown memo.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "The stock ticker symbol to analyze"},
                    "research_type": {"type": "string", "description": "Type of research (default: earnings_analysis)", "default": "earnings_analysis"}
                },
                "required": ["ticker"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool execution requests."""
    await ensure_initialized()
    
    if name == "get_market_snapshot":
        ticker = arguments.get("ticker", "").upper()
        if not ticker:
            return [types.TextContent(type="text", text="Error: Ticker is required.")]
        
        try:
            snapshot = await _market_client.get_snapshot(ticker)
            return [types.TextContent(type="text", text=json.dumps(snapshot, indent=2))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error fetching data: {str(e)}")]
            
    elif name == "run_investment_research":
        ticker = arguments.get("ticker", "").upper()
        res_type = arguments.get("research_type", "earnings_analysis")
        run_id = str(uuid.uuid4())
        
        # Register in audit DB
        await _audit.persist_run(
            run_id=run_id, ticker=ticker, company_name=ticker,
            research_type=res_type, requested_by="mcp_client",
        )
        
        initial_state = {
            "run_id": run_id,
            "ticker": ticker,
            "company_name": ticker,
            "research_type": res_type,
            "requested_by": "mcp_client",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "current_stage": "ingestion",
            "completed_stages": [],
            "errors": [],
            "raw_documents": [],
            "document_chunks": [],
            "retrieved_context": [],
            "sentiment_signals": [],
            "risk_flags": [],
            "extracted_tables": [],
            "extracted_figures": [],
            "chart_interpretations": [],
            "research_plan": {},
            "draft_memo": "",
            "cited_claims": [],
            "overall_confidence": 0.0,
            "hitl_required": False,
        }
        
        config = {"configurable": {"thread_id": run_id}, "recursion_limit": 50}
        
        try:
            # Run graph until end or interrupt
            await _graph.ainvoke(initial_state, config)
            
            # Check if it paused for HITL
            state_snapshot = await _graph.aget_state(config)
            
            if state_snapshot.next:
                # Automate approval for MCP
                from langgraph.types import Command
                resume_value = {
                    "decision": "approved",
                    "reviewer_id": "mcp_client",
                    "notes": "Auto-approved via MCP",
                }
                await _graph.aupdate_state(config, {}, as_node="hitl_router")
                await _graph.ainvoke(Command(resume=resume_value), config=config)
                state_snapshot = await _graph.aget_state(config)
                
            final_values = state_snapshot.values
            report = final_values.get("final_report", {})
            if isinstance(report, dict):
                memo = report.get("memo", "Error: No memo generated.")
            else:
                memo = str(report)
            
            # Persist audit log
            if final_values.get("audit_trail"):
                await _audit.persist_events(run_id, ticker, final_values["audit_trail"])
                
            return [types.TextContent(type="text", text=f"Research Run ID: {run_id}\n\n{memo}")]
            
        except Exception as e:
            logger.error("Graph execution failed in MCP", error=str(e))
            return [types.TextContent(type="text", text=f"Error running research: {str(e)}")]
            
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Use standard input/output for MCP communication
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
