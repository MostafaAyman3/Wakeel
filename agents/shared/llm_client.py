"""
Shared LLM Client — single source of truth for all language model instances.

Blueprint requirement (section 5.2):
    "LLM Client: one configured instance, used by all modules."

Exposes:
    llm_primary   : ChatOpenAI (gpt-4o)   — deep analysis, narrative, tax reasoning
    llm_fast      : ChatOpenAI (gpt-4o-mini) — classification, simple responses
    embeddings    : OpenAIEmbeddings (text-embedding-3-small) — Tax RAG (Sprint 4)

Usage in any agent node:
    from agents.shared.llm_client import llm_primary, llm_fast

    response = await llm_primary.ainvoke(messages)

Do NOT instantiate ChatOpenAI directly in node files.
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from backend.core.config import get_settings

settings = get_settings()

# Primary model — used for: deep analysis, narrative generation, tax reasoning,
# invoice pattern detection, and complex multi-step queries.
llm_primary = ChatOpenAI(
    model=settings.openai_model_primary,
    api_key=settings.openai_api_key,
    temperature=0.1,       # Low temperature for factual, deterministic responses
    max_tokens=2048,
    timeout=60,
    max_retries=2,
)

# Fast model — used for: intent classification, issue classification,
# simple status responses, and parameter extraction.
llm_fast = ChatOpenAI(
    model=settings.openai_model_fast,
    api_key=settings.openai_api_key,
    temperature=0.0,       # Zero temperature for deterministic classification
    max_tokens=512,
    timeout=30,
    max_retries=2,
)

# Embeddings — used for Tax RAG (Sprint 4).
# Dimension: 1536, matches VECTOR_EMBEDDING_DIMENSION in .env
embeddings = OpenAIEmbeddings(
    model=settings.openai_embedding_model,
    api_key=settings.openai_api_key,
    dimensions=settings.vector_embedding_dimension,
)
