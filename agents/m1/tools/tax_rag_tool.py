"""
Tax RAG Tool — Main Orchestrator for Tax Knowledge Retrieval and Generation.

Pipeline (end-to-end):
    1. normalize_arabic_query()   — clean Arabic query
    2. enhance_query()            — HyDE + multi-query → list of embeddings
    3. retrieve_multi()           — pgvector cosine search, deduplication
    4. Out-of-scope guard         — if no chunks pass threshold → refuse politely
    5. rerank_chunks()            — LLM scores chunks by legal relevance → top 3
    6. _build_context()           — format chunks with article/law citation
    7. llm_primary.ainvoke()      — GPT-4o generates answer from context only
    8. Return structured result   — answer + legal_reference + confidence + disclaimer

Result schema:
    {
        "answer":          str,          # GPT-4o generated answer
        "legal_reference": {             # From top reranked chunk (or None)
            "law":      str,             # "القانون رقم 67 لسنة 2016"
            "article":  str,             # "مادة 3"
            "document": str,             # document_name
        } | None,
        "confidence":      float,        # top rerank_score normalised to [0.0, 1.0]
        "sources":         list[str],    # chunk_ids used as context
        "disclaimer":      str,          # ALWAYS included — mandatory
        "out_of_scope":    bool,         # True if no relevant chunks found
    }

DISCLAIMER (mandatory, always appended):
    "توجيه استرشادي — استشر مستشاراً ضريبياً للقرارات الرسمية"
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from agents.shared.llm_client import llm_primary
from backend.core.database import get_readonly_session
from backend.services.rag.query_enhancer import enhance_query, normalize_arabic_query
from backend.services.rag.reranker import rerank_chunks
from backend.services.rag.retriever import retrieve_multi

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

DISCLAIMER = "توجيه استرشادي — استشر مستشاراً ضريبياً للقرارات الرسمية"

_TOP_K_RETRIEVAL = 5     # chunks per embedding query (before dedup + rerank)
_TOP_N_RERANK    = 3     # final chunks kept after LLM reranking
_THRESHOLD       = 0.75  # minimum cosine similarity to include a chunk

_OUT_OF_SCOPE_AR = (
    "عذراً، لم أجد في قاعدة المعرفة الضريبية ما يُجيب على هذا السؤال بشكل موثوق. "
    "يُرجى استشارة مستشار ضريبي مختص للحصول على إجابة دقيقة."
)
_OUT_OF_SCOPE_EN = (
    "I'm sorry, I could not find a reliable answer to this question "
    "in the available tax knowledge base. Please consult a qualified tax advisor."
)

# ── LLM prompts ────────────────────────────────────────────────────────────────

_GENERATION_SYSTEM = """أنت مستشار ضريبي قانوني متخصص في القانون الضريبي المصري.
مهمتك: الإجابة على الأسئلة الضريبية بدقة واحترافية مستنداً فقط إلى النصوص القانونية المُقدَّمة.

قواعد صارمة:
1. أجب فقط مما هو موجود في السياق القانوني المُعطى — لا تخمّن ولا تضف معلومات من خارجه
2. اذكر رقم المادة والقانون عند الاستشهاد (مثال: "وفقاً للمادة 3 من القانون رقم 67 لسنة 2016")
3. إذا كان السؤال خارج نطاق النصوص المتاحة، قل ذلك صراحةً
4. أجب بنفس لغة السؤال (عربي ← عربي / إنجليزي ← إنجليزي)
5. كن موجزاً ودقيقاً — لا تُطوّل بلا فائدة"""

_GENERATION_HUMAN = """السياق القانوني:
{context}

السؤال: {query}

أجب بشكل قانوني دقيق مستنداً إلى النص أعلاه فقط."""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def run_tax_rag(query: str, language: str = "ar") -> dict:
    """
    Full Tax RAG pipeline: enhance → retrieve → rerank → generate.

    Args:
        query:    User's tax question (Arabic or English, raw input).
        language: "ar" | "en" — controls variation direction in query_enhancer.

    Returns:
        TaxRAGResult dict (see module docstring for full schema).
        "disclaimer" is always present regardless of out_of_scope.
    """
    normalized = normalize_arabic_query(query)
    logger.info("tax_rag_tool.run_tax_rag: query='%s…' language=%s", query[:60], language)

    # ── Step 1: Query enhancement → multiple embeddings ───────────────────
    try:
        query_embeddings = await enhance_query(normalized or query, language)
    except Exception as exc:
        logger.error("enhance_query failed: %s", exc)
        query_embeddings = []

    if not query_embeddings:
        logger.error("No embeddings produced — returning out_of_scope")
        return _out_of_scope_result(language)

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
        return _out_of_scope_result(language)

    logger.debug("Retrieved %d deduplicated chunks above threshold", len(chunks))

    # ── Step 3: Out-of-scope guard ────────────────────────────────────────
    if not chunks:
        logger.info("No chunks above similarity threshold — out of scope")
        return _out_of_scope_result(language)

    # ── Step 4: LLM reranking → top N chunks ─────────────────────────────
    try:
        top_chunks = await rerank_chunks(query, chunks, top_n=_TOP_N_RERANK)
    except Exception as exc:
        logger.warning("rerank_chunks failed: %s — falling back to retrieval order", exc)
        top_chunks = chunks[:_TOP_N_RERANK]
        for chunk in top_chunks:
            chunk["rerank_score"] = chunk.get("similarity", 0.0)

    if not top_chunks:
        return _out_of_scope_result(language)

    # ── Step 5: Build context string ──────────────────────────────────────
    context = _build_context(top_chunks)
    sources = [c["chunk_id"] for c in top_chunks]

    # ── Step 6: Generate answer with GPT-4o ──────────────────────────────
    try:
        answer = await _generate_answer(query, context)
    except Exception as exc:
        logger.error("GPT-4o generation failed: %s", exc)
        answer = (
            "حدث خطأ أثناء توليد الإجابة. يُرجى المحاولة مرة أخرى."
            if language == "ar"
            else "An error occurred while generating the answer. Please try again."
        )

    # ── Step 7: Assemble result ───────────────────────────────────────────
    top       = top_chunks[0]
    legal_ref = _build_legal_reference(top)
    raw_score = top.get("rerank_score", top.get("similarity", 0.0))
    # rerank_score is 0-10 (LLM score); similarity is 0-1 (cosine) — normalise both to [0,1]
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
        "tax_rag_tool: done | confidence=%.3f | chunks_used=%d | top=%s",
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
    """
    Format reranked chunks into a numbered context block.

    Each block is prefixed with its article and law citation so GPT-4o
    can produce grounded, citable answers.
    """
    parts: list[str] = []

    for i, chunk in enumerate(chunks, start=1):
        article  = chunk.get("article", "")
        law      = chunk.get("law_number", "")
        doc      = chunk.get("document_name", "")
        text     = chunk.get("chunk_text", "")

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


def _out_of_scope_result(language: str) -> dict:
    """Standardised out-of-scope response — disclaimer always included."""
    return {
        "answer":          _OUT_OF_SCOPE_AR if language == "ar" else _OUT_OF_SCOPE_EN,
        "legal_reference": None,
        "confidence":      0.0,
        "sources":         [],
        "disclaimer":      DISCLAIMER,
        "out_of_scope":    True,
    }
