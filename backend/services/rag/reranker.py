"""
Reranker — LLM-Based Chunk Reranking for Arabic Tax Retrieval.

Why LLM reranking (not cross-encoder):
    - Cosine similarity measures linguistic similarity, not legal relevance
    - A chunk mentioning "ضريبة" might rank high but not answer the question
    - GPT-4o-mini understands Arabic legal context and judges true relevance
    - No need for a separate Arabic cross-encoder model

Strategy:
    1. Receive up to 15 deduplicated chunks from retriever
    2. Ask GPT-4o-mini to score each chunk 0-10 for relevance to query
    3. Return top_n (default: 3) highest-scored chunks
    4. On any failure → fall back to original cosine similarity order

LLM used: llm_fast (GPT-4o-mini)
Response:  JSON  {"scores": [8, 3, 9, 2, 7, ...]}
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from agents.shared.llm_client import llm_fast

logger = logging.getLogger(__name__)

# Max chars shown per chunk in the rerank prompt (controls token usage)
_CHUNK_PREVIEW_CHARS = 350

_RERANK_SYSTEM = """أنت خبير قانوني ضريبي متخصص في القانون المصري.
مهمتك: تقييم مدى صلة كل مقطع قانوني بالسؤال المطروح.
قواعد التقييم:
- 10: إجابة مباشرة وكاملة للسؤال
-  7: صلة قوية، يحتوي معلومات مفيدة
-  4: صلة جزئية أو غير مباشرة
-  1: لا صلة تذكر بالسؤال
أعد JSON فقط بدون أي نص إضافي: {{"scores": [رقم, رقم, ...]}}
عدد الأرقام يجب أن يساوي عدد المقاطع بالضبط."""

_RERANK_HUMAN = """السؤال: {query}

المقاطع القانونية:
{chunks_text}

قيّم كل مقطع من 0 إلى 10."""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_n: int = 3,
) -> list[dict]:
    """
    Rerank retrieved chunks by legal relevance to the query.

    Skips LLM call if chunks <= top_n (no reranking needed).
    Falls back to cosine similarity order if LLM call fails.

    Args:
        query:  Original user query (AR or EN).
        chunks: Deduplicated RetrievedChunk dicts from retriever.
        top_n:  Number of top chunks to return (default: 3).

    Returns:
        List of up to top_n RetrievedChunk dicts sorted by rerank score desc.
        Each chunk gets a "rerank_score" key added.
    """
    if not chunks:
        return []

    # No need to call LLM if we already have few enough chunks
    if len(chunks) <= top_n:
        for chunk in chunks:
            chunk["rerank_score"] = chunk.get("similarity", 0.0)
        return chunks

    prompt_text = build_rerank_prompt(query, chunks)

    messages = [
        SystemMessage(content=_RERANK_SYSTEM),
        HumanMessage(content=prompt_text),
    ]

    try:
        response = await llm_fast.ainvoke(messages)
        scores   = parse_rerank_scores(response.content, expected_count=len(chunks))

    except Exception as exc:
        logger.warning("Reranker LLM call failed: %s — using similarity order", exc)
        scores = [chunk.get("similarity", 0.0) for chunk in chunks]

    # Attach rerank scores and sort
    ranked = sorted(
        zip(scores, chunks),
        key=lambda pair: pair[0],
        reverse=True,
    )

    result = []
    for score, chunk in ranked[:top_n]:
        chunk["rerank_score"] = round(score, 4)
        result.append(chunk)

    logger.debug(
        "Reranker: %d → %d chunks | top score=%.1f",
        len(chunks), len(result), result[0]["rerank_score"] if result else 0,
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_rerank_prompt(query: str, chunks: list[dict]) -> str:
    """
    Build the scoring prompt body sent to GPT-4o-mini.

    Each chunk is shown with its index [0], [1], … and truncated to
    _CHUNK_PREVIEW_CHARS to keep total tokens manageable.
    Article and law metadata are prepended so the model has legal context.

    Args:
        query:  User query string.
        chunks: List of RetrievedChunk dicts.

    Returns:
        Formatted prompt string (the HumanMessage content).
    """
    lines: list[str] = []

    for i, chunk in enumerate(chunks):
        article  = chunk.get("article", "")
        law      = chunk.get("law_number", "")
        text     = chunk.get("chunk_text", "")[:_CHUNK_PREVIEW_CHARS]

        header   = f"[{i}]"
        if article:
            header += f" {article}"
        if law:
            header += f" — {law}"

        lines.append(f"{header}\n{text}")

    chunks_text = "\n\n---\n\n".join(lines)

    return _RERANK_HUMAN.format(query=query, chunks_text=chunks_text)


def parse_rerank_scores(response_text: str, expected_count: int) -> list[float]:
    """
    Parse JSON scores array from GPT-4o-mini response.

    Handles:
        - Markdown code fences (```json … ```)
        - Extra text before/after the JSON object
        - Missing or extra scores (pads / truncates to expected_count)
        - Non-numeric values in the scores array

    Falls back to uniform 5.0 scores if parsing fails entirely,
    so reranking never blocks the downstream pipeline.

    Args:
        response_text:  Raw content string from LLM response.
        expected_count: Number of scores expected (= len(chunks)).

    Returns:
        list[float] of length == expected_count.
    """
    fallback = [5.0] * expected_count

    try:
        text = response_text.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        # Extract first JSON object found in the response
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            logger.warning("parse_rerank_scores: no JSON object found in response")
            return fallback

        parsed = json.loads(json_match.group())
        raw_scores = parsed.get("scores", [])

        if not isinstance(raw_scores, list):
            logger.warning("parse_rerank_scores: 'scores' is not a list")
            return fallback

        # Convert to float, clamp to [0, 10]
        scores: list[float] = []
        for val in raw_scores:
            try:
                scores.append(max(0.0, min(10.0, float(val))))
            except (TypeError, ValueError):
                scores.append(5.0)

        # Align length to expected_count
        if len(scores) < expected_count:
            scores.extend([5.0] * (expected_count - len(scores)))
        else:
            scores = scores[:expected_count]

        return scores

    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("parse_rerank_scores failed: %s — using fallback", exc)
        return fallback
