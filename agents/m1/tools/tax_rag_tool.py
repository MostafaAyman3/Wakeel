"""
Tax RAG Tool — Main Orchestrator for Tax Knowledge Retrieval and Generation.

Pipeline (end-to-end):
    1. enhance_query()     — multi-query → list of embeddings (no HyDE)
    2. retrieve_multi()    — pgvector cosine search, deduplication
    3. Out-of-scope guard  — if no chunks pass threshold → refuse politely
    4. rerank_chunks()     — LLM scores chunks by legal relevance → top 3
    5. _build_context()    — format chunks with article/law citation
    6. llm_primary.ainvoke() — GPT-4o generates answer from context only
    7. _is_no_answer()     — detect if GPT-4o couldn't find a direct answer
    8. Return structured result

Result schema:
    {
        "answer":          str,
        "legal_reference": {"law": str, "article": str, "document": str} | None,
        "confidence":      float,        # [0.0, 1.0]
        "sources":         list[str],    # chunk_ids used
        "disclaimer":      str,          # ALWAYS included
        "out_of_scope":    bool,
    }
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from agents.shared.llm_client import llm_primary
from backend.core.database import get_readonly_session
from backend.services.rag.query_enhancer import enhance_query
from backend.services.rag.reranker import rerank_chunks
from backend.services.rag.retriever import retrieve_multi

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

DISCLAIMER = "Advisory guidance only — consult a qualified tax advisor for official decisions."

_TOP_K_RETRIEVAL = 5     # chunks per embedding query (before dedup + rerank)
_TOP_N_RERANK    = 3     # final chunks kept after LLM reranking
_THRESHOLD       = 0.50  # minimum cosine similarity to include a chunk

_OUT_OF_SCOPE = (
    "I'm sorry, I could not find a reliable answer to this question "
    "in the available tax knowledge base. "
    "Please consult a qualified tax advisor for an accurate answer."
)

# ── LLM prompts ────────────────────────────────────────────────────────────────

_GENERATION_SYSTEM = """You are a specialized legal tax advisor in Egyptian tax law.
Your task: answer tax questions accurately and professionally based ONLY on the provided legal texts.

Strict rules:
1. Answer only from the legal context provided — do not guess or add outside information
2. Cite the article and law when referencing a provision (e.g. "According to Article 3 of Law No. 91 of 2005")
3. If the retrieved texts do not contain a direct answer, do NOT infer absence of a legal ruling — say only: "I could not find a direct answer in the retrieved legal texts."
4. Be concise and precise"""

_GENERATION_HUMAN = """Legal context:
{context}

Question: {query}

Provide an accurate legal answer based solely on the above context."""

# Phrases that indicate GPT-4o couldn't find a direct answer in the retrieved context
_NO_ANSWER_PHRASES = [
    "i could not find a direct answer",
    "could not find a direct answer",
    "no direct answer",
    "not addressed in the retrieved",
    "not covered in the retrieved",
    "retrieved texts do not contain",
]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def run_tax_rag(query: str, language: str = "en") -> dict:
    """
    Full Tax RAG pipeline: enhance → retrieve → rerank → generate.

    Args:
        query:    User's tax question (English).
        language: "en" (reserved for future bilingual support).

    Returns:
        TaxRAGResult dict — "disclaimer" is always present.
    """
    logger.info("tax_rag_tool.run_tax_rag: query='%s…'", query[:60])

    # ── Step 1: Query enhancement → multiple embeddings ───────────────────
    try:
        query_embeddings = await enhance_query(query.strip(), language)
    except Exception as exc:
        logger.error("enhance_query failed: %s", exc)
        query_embeddings = []

    if not query_embeddings:
        logger.error("No embeddings produced — returning out_of_scope")
        return _out_of_scope_result()

    # ── Step 2: Retrieve from pgvector ────────────────────────────────────
    try:
        async with get_readonly_session() as db:
            chunks = await retrieve_multi(
                query_embeddings,
                db,
                top_k=_TOP_K_RETRIEVAL,
                threshold=_THRESHOLD,
            )
    except Exception as exc:
        logger.error("retrieve_multi failed: %s", exc)
        return _out_of_scope_result()

    logger.debug("Retrieved %d deduplicated chunks above threshold", len(chunks))

    # ── Step 3: Out-of-scope guard ────────────────────────────────────────
    if not chunks:
        logger.info("No chunks above similarity threshold — out of scope")
        return _out_of_scope_result()

    # ── Step 4: LLM reranking → top N chunks ─────────────────────────────
    try:
        top_chunks = await rerank_chunks(query, chunks, top_n=_TOP_N_RERANK)
    except Exception as exc:
        logger.warning("rerank_chunks failed: %s — falling back to retrieval order", exc)
        top_chunks = chunks[:_TOP_N_RERANK]
        for chunk in top_chunks:
            chunk["rerank_score"] = chunk.get("similarity", 0.0)

    if not top_chunks:
        return _out_of_scope_result()

    # ── Step 5: Build context string ──────────────────────────────────────
    context = _build_context(top_chunks)
    sources = [c["chunk_id"] for c in top_chunks]

    # ── Step 6: Generate answer with GPT-4o ──────────────────────────────
    try:
        answer = await _generate_answer(query, context)
    except Exception as exc:
        logger.error("GPT-4o generation failed: %s", exc)
        answer = "An error occurred while generating the answer. Please try again."

    # ── Step 7: Detect "no direct answer" from GPT-4o ────────────────────
    if _is_no_answer(answer):
        logger.info("GPT-4o indicated no direct answer — marking out_of_scope")
        return {
            "answer":          answer,
            "legal_reference": None,
            "confidence":      0.0,
            "sources":         sources,
            "disclaimer":      DISCLAIMER,
            "out_of_scope":    True,
        }

    # ── Step 8: Assemble result ───────────────────────────────────────────
    top       = top_chunks[0]
    legal_ref = _build_legal_reference(top)
    raw_score = top.get("rerank_score", top.get("similarity", 0.0))
    confidence = round(raw_score / 10.0 if raw_score > 1.0 else float(raw_score), 3)

    result = {
        "answer":          answer,
        "legal_reference": legal_ref,
        "confidence":      confidence,
        "sources":         sources,
        "disclaimer":      DISCLAIMER,
        "out_of_scope":    False,
    }

    logger.info(
        "tax_rag_tool: done | confidence=%.3f | chunks=%d | top=%s",
        confidence, len(sources), sources[0] if sources else "—",
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _generate_answer(query: str, context: str) -> str:
    """Invoke llm_primary (GPT-4o) with context + query → return answer text."""
    messages = [
        SystemMessage(content=_GENERATION_SYSTEM),
        HumanMessage(content=_GENERATION_HUMAN.format(context=context, query=query)),
    ]
    response = await llm_primary.ainvoke(messages)
    return response.content.strip()


def _build_context(chunks: list[dict]) -> str:
    """Format reranked chunks into a numbered context block."""
    parts: list[str] = []

    for i, chunk in enumerate(chunks, start=1):
        article = chunk.get("article", "")
        law     = chunk.get("law_number", "")
        doc     = chunk.get("document_name", "")
        text    = chunk.get("chunk_text", "")

        header = f"[{i}]"
        if article:
            header += f" {article}"
        if law:
            header += f" | {law}"
        if doc and doc != law:
            header += f" | {doc}"

        parts.append(f"{header}\n{text}")

    return "\n\n---\n\n".join(parts)


def _build_legal_reference(chunk: dict) -> dict | None:
    """Extract structured legal reference from the top reranked chunk."""
    law      = chunk.get("law_number",    "").strip()
    article  = chunk.get("article",       "").strip()
    document = chunk.get("document_name", "").strip()

    if not any([law, article, document]):
        return None

    return {"law": law, "article": article, "document": document}


def _is_no_answer(answer: str) -> bool:
    """Return True if GPT-4o indicated it couldn't find a direct answer."""
    lower = answer.lower()
    return any(phrase in lower for phrase in _NO_ANSWER_PHRASES)


def _out_of_scope_result() -> dict:
    """Standardised out-of-scope response — disclaimer always included."""
    return {
        "answer":          _OUT_OF_SCOPE,
        "legal_reference": None,
        "confidence":      0.0,
        "sources":         [],
        "disclaimer":      DISCLAIMER,
        "out_of_scope":    True,
    }
