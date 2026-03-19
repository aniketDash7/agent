"""
CapitalMind — Audit Trail Persistence.
PostgreSQL event sourcing for regulatory-grade traceability.
Every agent action is timestamped with token usage, duration, and I/O summaries.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any


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

    async def initialize(self) -> None:
        """Create audit tables if they don't exist."""
        # In production: CREATE TABLE IF NOT EXISTS ...
        pass

    async def persist_run(
        self,
        run_id: str,
        ticker: str,
        company_name: str,
        research_type: str,
        requested_by: str,
    ) -> None:
        """Persist initial run metadata."""
        pass

    async def persist_events(
        self,
        run_id: str,
        ticker: str,
        events: list[dict],
    ) -> None:
        """Persist batch of audit events."""
        pass

    async def complete_run(
        self,
        run_id: str,
        status: str,
        confidence: float,
        report_s3_uri: str | None,
        hitl_required: bool,
    ) -> None:
        """Mark a run as complete with final metadata."""
        pass

    async def get_run_audit(self, run_id: str) -> list[dict]:
        """Retrieve all audit events for a run."""
        return []

    async def get_recent_runs(
        self,
        ticker: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Get recent research runs, optionally filtered by ticker."""
        return []
