"""
CapitalMind — Application Settings.
Pydantic settings class with environment variable support.
Configured for local development with Ollama (no API keys required).
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

    # ── Ollama (Local LLM) ───────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    primary_model: str = "llama3.2:3b"        # Main reasoning LLM
    vision_model: str = "qwen3.5:2b"           # Multimodal / chart interpretation
    embedding_model: str = "mxbai-embed-large"  # Local embeddings (1024-dim)
    embedding_dim: int = 1024

    # ── Vector Store ─────────────────────────────────────────────────────────
    pinecone_api_key: SecretStr = SecretStr("pcsk_FJShz_BAUgCZEpZs2ZCwjW51ATStZNVgczT1QEwdKCEN44eBeAo1MU9c91a7zbVs5gRde")
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

    # ── AWS (optional — for production S3 uploads) ───────────────────────────
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
