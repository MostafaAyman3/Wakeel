"""
Query Enhancer — HyDE + Multi-Query Expansion for Arabic Tax Queries.

Techniques applied (in order):
    1. Arabic Normalization  — normalize query before embedding
    2. HyDE                  — generate hypothetical legal answer → embed it
    3. Multi-Query Expansion — generate 3 query variations (AR synonyms + EN)

Why these techniques for Arabic legal:
    - User writes in colloquial Egyptian Arabic ("إيه نسبة الـ VAT؟")
    - Law text is in formal Modern Standard Arabic (MSA)
    - HyDE bridges this gap: generates MSA legal phrasing automatically
    - Multi-query catches synonyms (ضريبة القيمة المضافة / ضريبة المبيعات)

LLM used: llm_fast (GPT-4o-mini) — query enhancement is low-stakes, speed matters
Embedder: agents.shared.llm_client.embeddings (text-embedding-3-small, 1536 dims)

Output of enhance_query():
    Up to 4 embeddings returned:
        [hyde_embedding, var1_embedding, var2_embedding, var3_embedding]
    On any partial failure the pipeline degrades gracefully:
        - HyDE fails  → falls back to embedding the original query
        - Variations fail → only HyDE embedding is returned
"""

from __future__ import annotations

import asyncio
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from agents.shared.llm_client import embeddings as _embeddings
from agents.shared.llm_client import llm_fast

logger = logging.getLogger(__name__)

# ── Arabic normalization patterns (identical to pdf_loader.normalize_arabic) ──
_TASHKEEL = re.compile(
    r"[ؐ-ًؚ-ٟۖ-ۜ۟-۪ۤۧۨ-ۭ]"
)
_ALEF     = re.compile(r"[أإآٱ]")
_TEH_MARB = re.compile(r"ة")
_YEH      = re.compile(r"ى")
_MULTI_SP = re.compile(r"[ \t]+")

# ── LLM prompts ────────────────────────────────────────────────────────────────
_HYDE_SYSTEM = """أنت مستشار ضريبي متخصص في القانون الضريبي المصري.
اكتب فقرة قانونية رسمية مختصرة (3-4 جمل) كأنك تقتبس مباشرة من نص القانون.
أجب على السؤال بأسلوب قانوني رسمي دقيق.
لا تضف مقدمات — ابدأ بالإجابة مباشرةً."""

_HYDE_HUMAN = "السؤال: {query}"

_VARIATIONS_SYSTEM = """أنت متخصص في اللغة القانونية العربية.
مهمتك: إعادة صياغة سؤال ضريبي بثلاث طرق مختلفة.
القواعد:
- الصياغة الأولى:  بالعربية الفصحى الرسمية (مصطلحات قانونية)
- الصياغة الثانية: بالعربية مع مرادفات مختلفة للمصطلح الرئيسي
- الصياغة الثالثة: بالإنجليزية (إذا كان السؤال بالعربية) أو بالعربية (إذا كان بالإنجليزية)
أعد النتيجة كـ JSON فقط: {{"variations": ["الصياغة 1", "الصياغة 2", "الصياغة 3"]}}"""

_VARIATIONS_HUMAN = "السؤال الأصلي: {query}"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def enhance_query(query: str, language: str = "ar") -> list[list[float]]:
    """
    Full query enhancement pipeline: normalize → HyDE → multi-query.

    All LLM calls run concurrently (asyncio.gather) for minimal latency.
    Degrades gracefully on failure — always returns at least one embedding.

    Args:
        query:    Raw user query in Arabic or English.
        language: "ar" | "en"  (used for variation prompt direction)

    Returns:
        List of 1-4 embedding vectors (list[float], len=1536 each):
            [hyde_embedding, var1_embedding, var2_embedding, var3_embedding]
        Falls back to [original_query_embedding] if all LLM calls fail.
    """
    normalized = normalize_arabic_query(query)

    # Run HyDE and multi-query generation concurrently
    hyde_task       = asyncio.create_task(generate_hyde_embedding(normalized))
    variations_task = asyncio.create_task(generate_query_variations(normalized, language))

    hyde_embedding: list[float] | None = None
    variations:     list[str]          = []

    try:
        hyde_embedding, variations = await asyncio.gather(
            hyde_task, variations_task, return_exceptions=True
        )
    except Exception as exc:
        logger.warning("enhance_query gather failed: %s", exc)

    # Handle exceptions returned by gather (return_exceptions=True)
    if isinstance(hyde_embedding, Exception):
        logger.warning("HyDE failed: %s — falling back to original query embedding", hyde_embedding)
        hyde_embedding = None

    if isinstance(variations, Exception):
        logger.warning("Multi-query failed: %s — skipping variations", variations)
        variations = []

    # Collect all texts to embed in one batch call
    texts_to_embed: list[str] = []

    if hyde_embedding is None:
        # HyDE failed → embed the original normalized query as fallback
        texts_to_embed.append(normalized)
    # (HyDE already returned an embedding — no need to re-embed)

    texts_to_embed.extend(v for v in variations if v.strip())

    # Embed all at once
    batch_embeddings: list[list[float]] = []
    if texts_to_embed:
        try:
            batch_embeddings = await _embeddings.aembed_documents(texts_to_embed)
        except Exception as exc:
            logger.error("Batch embedding for variations failed: %s", exc)
            batch_embeddings = []

    # Build final result list
    result: list[list[float]] = []

    if hyde_embedding is not None:
        result.append(hyde_embedding)
    elif batch_embeddings:
        # First item was the fallback original query
        result.append(batch_embeddings.pop(0))

    result.extend(batch_embeddings)   # remaining are variation embeddings

    if not result:
        # Last resort: embed the raw query synchronously
        logger.error("All enhancement steps failed — embedding raw query")
        raw_embedding = await _embeddings.aembed_query(normalized or query)
        result.append(raw_embedding)

    logger.debug("enhance_query → %d embeddings produced", len(result))
    return result


async def generate_hyde_embedding(query: str) -> list[float]:
    """
    HyDE: generate a hypothetical MSA legal answer and return its embedding.

    The hypothetical answer is NOT returned to the user — it is used only
    as an intermediate representation to retrieve more relevant law chunks.

    Why: embedding a question produces a vector far from legal document text.
         Embedding a legal-style answer is much closer to chunk embeddings.

    Args:
        query: Normalized user query.

    Returns:
        1536-dim embedding of the hypothetical answer text.

    Raises:
        Exception: Propagates OpenAI errors — caller handles gracefully.
    """
    messages = [
        SystemMessage(content=_HYDE_SYSTEM),
        HumanMessage(content=_HYDE_HUMAN.format(query=query)),
    ]

    response          = await llm_fast.ainvoke(messages)
    hypothetical_text = response.content.strip()

    logger.debug("HyDE hypothetical answer (%d chars): %s…",
                 len(hypothetical_text), hypothetical_text[:80])

    embedding = await _embeddings.aembed_query(hypothetical_text)
    return embedding


async def generate_query_variations(query: str, language: str = "ar") -> list[str]:
    """
    Generate 3 query variations using GPT-4o-mini.

    Variation strategy:
        1. MSA Arabic with formal legal terminology
        2. Arabic with alternative synonyms for the main concept
        3. English translation (if Arabic input) / Arabic translation (if English)

    Falls back to an empty list on any error — the caller skips variations
    and continues with only the HyDE embedding.

    Args:
        query:    Normalized user query.
        language: "ar" | "en"

    Returns:
        List of exactly 3 non-empty variation strings.
        Returns [] if LLM call or JSON parsing fails.
    """
    messages = [
        SystemMessage(content=_VARIATIONS_SYSTEM),
        HumanMessage(content=_VARIATIONS_HUMAN.format(query=query)),
    ]

    try:
        response = await llm_fast.ainvoke(messages)
        raw      = response.content.strip()

        # Strip markdown code fences if model wraps in ```json
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        import json
        parsed     = json.loads(raw)
        variations = parsed.get("variations", [])

        # Filter: must be list of 3 non-empty strings
        valid = [v.strip() for v in variations if isinstance(v, str) and v.strip()]

        if len(valid) < 2:
            logger.warning("Too few valid variations (%d) — skipping", len(valid))
            return []

        logger.debug("Multi-query: %d variations generated", len(valid))
        return valid[:3]

    except Exception as exc:
        logger.warning("generate_query_variations failed: %s", exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────────────────────

def normalize_arabic_query(query: str) -> str:
    """
    Normalize an Arabic query using the same rules as pdf_loader.normalize_arabic().

    Applying identical normalization to both stored chunks and incoming queries
    ensures that embedding similarity is measured on comparable representations.

    Operations:
        1. Remove tashkeel (diacritics / Quranic marks)
        2. Unify Alef forms: أ إ آ ٱ → ا
        3. Unify Teh Marbuta: ة → ه
        4. Unify Alef Maqsura: ى → ي
        5. Collapse multiple spaces / tabs → single space
        6. Strip leading / trailing whitespace

    Args:
        query: Raw user query (may be Arabic, English, or mixed).

    Returns:
        Normalized string. Non-Arabic characters are passed through unchanged.
    """
    if not query:
        return ""

    query = _TASHKEEL.sub("", query)
    query = _ALEF.sub("ا", query)
    query = _TEH_MARB.sub("ه", query)
    query = _YEH.sub("ي", query)
    query = _MULTI_SP.sub(" ", query)
    return query.strip()
