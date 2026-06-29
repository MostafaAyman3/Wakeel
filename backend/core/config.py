"""
Application configuration using Pydantic Settings.
Reads all values from environment variables / .env file.

NOTE: load_dotenv() is called at module level so that LANGCHAIN_*
env vars are present in os.environ BEFORE LangChain/LangGraph
import-time checks (they don't read pydantic Settings).
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = 2 levels up from backend/core/config.py
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"

# ── Inject .env into os.environ (for LangChain / LangSmith) ─────
load_dotenv(_ENV_FILE, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


    # Application
    app_env: str = "development"
    app_name: str = "AERIE"
    app_version: str = "0.1.0"
    api_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:3000"

    # Database — main read-write connection (Supabase Shared Pooler, asyncpg)
    database_url: str

    # Database — read-only connection for M1 agent queries (SELECT only)
    readonly_db_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_hours: int = 8
    refresh_token_expire_days: int = 7
    confirmation_token_ttl_minutes: int = 10

    # OpenAI
    openai_api_key: str
    openai_model_primary: str = "gpt-4o"
    openai_model_fast: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    vector_embedding_dimension: int = 1536

    # ElevenLabs
    elevenlabs_api_key: str = ""

    # LangChain / LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "aerie-mvp"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # pgvector / Tax RAG
    tax_docs_path: str = "./data/tax_knowledge_base"
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.75

    # M1 architecture migration
    m1_stratified_router_enabled: bool = True
    m1_nl2sql_enabled: bool = True
    m1_shadow_router_enabled: bool = False
    m1_react_max_iterations: int = 5
    m1_nl2sql_max_attempts: int = 3
    m1_max_db_executions: int = 4
    m1_query_timeout_ms: int = 30000
    m1_query_hard_limit: int = 500

    # M2 n8n webhooks
    n8n_rfq_webhook_url: str = ""

    # Mini-RAG microservice
    mini_rag_base_url: str = "http://localhost:8001"
    rag_support_kb_project_id: int = 1
    rag_tax_project_id: int = 2

    # M3 thresholds
    m3_repeat_issue_threshold: int = 2
    m3_confidence_review_threshold: float = 0.70
    m3_clarification_max_attempts: int = 2  # Feature 004: ask N times then escalate
    m3_invalid_id_max_attempts: int = 3     # Feature 006: retry N times then show menu
    m3_alt_lookup_enabled: bool = False     # Feature 006: enable phone/email alt-lookup menu choice

    # Frontend
    next_public_api_base_url: str = "http://localhost:8000"
    next_public_ws_base_url: str = "ws://localhost:8000"

    @field_validator("database_url", "readonly_db_url")
    @classmethod
    def must_be_postgresql(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DB URL must start with 'postgresql'")
        return v


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Import this in all modules."""
    return Settings()
