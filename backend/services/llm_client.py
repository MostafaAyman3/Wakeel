"""
Backend LLM client service — re-exports the shared LLM instances
for use in backend services (orchestrators, etc.).

Backend services should import from here rather than from agents/shared
to maintain clean layer boundaries.

Usage:
    from backend.services.llm_client import llm_primary, llm_fast, embeddings
"""

from agents.shared.llm_client import embeddings, llm_fast, llm_primary

__all__ = ["llm_primary", "llm_fast", "embeddings"]
