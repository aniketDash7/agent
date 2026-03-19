"""
CapitalMind — Application Settings.
Pydantic settings class with environment variable support.
"""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import SecretStr


class Settings(BaseSettings):
    """Application configuration driven by environment variables / .env file."""

    # ── Application ──────────────────────────────────────────────────────────
    app_env: str = "development"
    app_name: str = "CapitalMind"
    debug: bool = True

    # ── LLM Configuration ────────────────────────────────────────────────────
    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    primary_model: str = "claude-sonnet-4-20250514"
    vision_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-large"
    embedding_dim: int = 3072

    # ── Vector Store ─────────────────────────────────────────────────────────
    pinecone_api_key: SecretStr = SecretStr("")
    pinecone_index: str = "capitalmind"
    retrieval_top_k: int = 8

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/capitalmind"

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ── HITL / Quality ───────────────────────────────────────────────────────
    hitl_confidence_threshold: float = 0.80
    quality_threshold: float = 0.75
    agent_max_iterations: int = 5

    # ── AWS ───────────────────────────────────────────────────────────────────
    aws_region: str = "us-east-1"
    s3_bucket: str = "capitalmind-reports"

    # ── Observability ────────────────────────────────────────────────────────
    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_project: str = "capitalmind"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
