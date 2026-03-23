"""
CapitalMind — Audit Trail Persistence.
PostgreSQL event sourcing for regulatory-grade traceability.
Every agent action is timestamped with token usage, duration, and I/O summaries.
"""
import json
import uuid
import structlog
from datetime import datetime, timezone
from typing import Any
from psycopg_pool import AsyncConnectionPool
from src.utils.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

class AuditLogger:
    """Creates structured audit events for the graph's audit_trail list."""

    def create_event(
        self,
        stage: str,
        agent: str,
        action: str,
        input_summary: str,
        output_summary: str,
        duration_ms: int = 0,
        model_used: str = "",
        token_usage: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a structured audit event dict (AuditEvent schema)."""
        return {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage if isinstance(stage, str) else stage.value,
            "agent": agent,
            "action": action,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "duration_ms": duration_ms,
            "model_used": model_used,
            "token_usage": token_usage or {},
            "metadata": metadata or {},
        }


class AuditPersister:
    """Persists audit events and run metadata to PostgreSQL."""

    def __init__(self):
        conn_str = settings.database_url.replace("+asyncpg", "")
        self.pool = AsyncConnectionPool(conninfo=conn_str, max_size=10, open=False)

    async def initialize(self) -> None:
        """Create audit tables if they don't exist."""
        if self.pool.closed:
            await self.pool.open()

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS research_runs (
                        run_id UUID PRIMARY KEY,
                        ticker TEXT,
                        company_name TEXT,
                        research_type TEXT,
                        requested_by TEXT,
                        status TEXT DEFAULT 'running',
                        confidence FLOAT DEFAULT 0.0,
                        report_s3_uri TEXT,
                        hitl_required BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id UUID PRIMARY KEY,
                        run_id UUID REFERENCES research_runs(run_id) ON DELETE CASCADE,
                        timestamp TIMESTAMP WITH TIME ZONE,
                        stage TEXT,
                        agent TEXT,
                        action TEXT,
                        input_summary TEXT,
                        output_summary TEXT,
                        duration_ms INTEGER,
                        model_used TEXT,
                        token_usage JSONB,
                        metadata JSONB
                    );
                    CREATE INDEX IF NOT EXISTS idx_audit_run_id ON audit_events(run_id);
                """)

    async def persist_run(
        self,
        run_id: str,
        ticker: str,
        company_name: str,
        research_type: str,
        requested_by: str,
    ) -> None:
        """Persist initial run metadata."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO research_runs (run_id, ticker, company_name, research_type, requested_by)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (run_id) DO NOTHING
                """, (run_id, ticker, company_name, research_type, requested_by))

    async def persist_events(
        self,
        run_id: str,
        ticker: str,
        events: list[dict],
    ) -> None:
        """Persist batch of audit events."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                for ev in events:
                    await cur.execute("""
                        INSERT INTO audit_events (
                            event_id, run_id, timestamp, stage, agent, action, 
                            input_summary, output_summary, duration_ms, model_used, 
                            token_usage, metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (event_id) DO NOTHING
                    """, (
                        ev["event_id"], run_id, ev["timestamp"], ev["stage"], 
                        ev["agent"], ev["action"], ev["input_summary"], 
                        ev["output_summary"], ev["duration_ms"], ev["model_used"],
                        json.dumps(ev.get("token_usage", {})), json.dumps(ev.get("metadata", {}))
                    ))

    async def complete_run(
        self,
        run_id: str,
        status: str,
        confidence: float,
        report_s3_uri: str | None,
        hitl_required: bool,
    ) -> None:
        """Mark a run as complete with final metadata."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    UPDATE research_runs 
                    SET status = %s, confidence = %s, report_s3_uri = %s, 
                        hitl_required = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE run_id = %s
                """, (status, confidence, report_s3_uri, hitl_required, run_id))

    async def get_run_audit(self, run_id: str) -> list[dict]:
        """Retrieve all audit events for a run."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT * FROM audit_events WHERE run_id = %s ORDER BY timestamp ASC
                """, (run_id,))
                columns = [desc[0] for desc in cur.description]
                rows = await cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]

    async def get_recent_runs(
        self,
        ticker: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Get recent research runs, optionally filtered by ticker."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                if ticker:
                    await cur.execute("""
                        SELECT * FROM research_runs WHERE ticker = %s ORDER BY created_at DESC LIMIT %s
                    """, (ticker.upper(), limit))
                else:
                    await cur.execute("""
                        SELECT * FROM research_runs ORDER BY created_at DESC LIMIT %s
                    """, (limit,))
                columns = [desc[0] for desc in cur.description]
                rows = await cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
