"""
Chunker — Advanced Hierarchical Semantic Chunking for Arabic Legal Documents.

Strategy (3 phases per document):

    Phase 1 — Structural Parsing (Rule-based, free)
        Regex detects document hierarchy: الباب → الفصل → المادة
        Each مادة becomes a candidate chunk with inherited metadata.

    Phase 2 — Size Gate
        If candidate <= MAX_CHUNK_CHARS  →  keep as single chunk (no LLM)
        If candidate >  MAX_CHUNK_CHARS  →  send to Phase 3

    Phase 3 — LLM Semantic Split (GPT-4o-mini, cheap)
        Sends the oversized article to GPT-4o-mini.
        LLM identifies semantic boundaries within the article.
        Returns 2-4 sub-chunks that each cover one legal concept.
        Fallback: paragraph split if LLM response is malformed.

Why LLM for large articles:
    - Some Egyptian law articles contain multiple فقرات that are semantically
      distinct but structurally merged — fixed-size splitting breaks context.
    - GPT-4o-mini understands Arabic legal structure and returns coherent splits.
    - Used ONLY for oversized articles (~20% of chunks), keeping cost minimal.

Model used:  llm_fast (GPT-4o-mini) — cheap, fast, sufficient for splitting
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from agents.shared.llm_client import llm_fast

logger = logging.getLogger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────────
MAX_CHUNK_CHARS = 1800   # ~450 Arabic tokens — above this triggers LLM split
OVERLAP_CHARS   = 150    # overlap appended between paragraph sub-chunks

# ── Structural regex patterns (Egyptian law conventions) ──────────────────────
# مادة 3 | مادة (3) | المادة الثالثة | ماده 5
_ARTICLE_SPLIT_RE = re.compile(
    r"(\n\s*(?:ال)?ماده?\s*(?:\(\s*\d+\s*\)|\d+\s*[-–]?\s*\d*|[أ-ي]+(?:\s+[أ-ي]+)?))",
    re.UNICODE,
)

# الباب الأول | الباب الثاني | الباب 1
_CHAPTER_RE = re.compile(
    r"^\s*(الباب\s+(?:[أ-ي]+|\d+)(?:\s+[أ-ي\s]+)?)",
    re.MULTILINE | re.UNICODE,
)

# الفصل الأول | الفصل الثاني
_SECTION_RE = re.compile(
    r"^\s*(الفصل\s+(?:[أ-ي]+|\d+)(?:\s+[أ-ي\s]+)?)",
    re.MULTILINE | re.UNICODE,
)

# مادة X — for citation extraction
_ARTICLE_LABEL_RE = re.compile(
    r"(?:ال)?ماده?\s*(?:\(\s*(\d+)\s*\)|(\d+)|([أ-ي]+(?:\s+[أ-ي]+)?))",
    re.UNICODE,
)

# ── LLM prompts ────────────────────────────────────────────────────────────────
_SPLIT_SYSTEM = """أنت خبير في تحليل وتقسيم النصوص القانونية العربية.
مهمتك: تقسيم النص القانوني إلى أجزاء دلالية متماسكة.
قواعد صارمة:
- لا تُعدّل أي كلمة في النص — انسخه حرفياً
- كل جزء يغطي فكرة قانونية واحدة متكاملة
- عدد الأجزاء: بين 2 و 4 فقط
- أعد النتيجة بصيغة JSON فقط بدون أي نص إضافي"""

_SPLIT_HUMAN = """قسّم النص القانوني التالي إلى أجزاء دلالية.
أعد: {{"segments": ["الجزء الأول...", "الجزء الثاني...", ...]}}

النص:
{article_text}"""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def chunk_all_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk all ProcessedDocuments and return a flat list of chunks.

    Args:
        documents: List of ProcessedDocument dicts from pdf_loader.

    Returns:
        Flat list of Chunk dicts across all documents, globally indexed.
    """
    all_chunks: list[dict] = []

    for document in documents:
        logger.info("Chunking: %s", document["document_name"] or document["source_file"])
        doc_chunks = await chunk_document(document)
        all_chunks.extend(doc_chunks)
        logger.info("  → %d chunks", len(doc_chunks))

    logger.info("Total chunks across all documents: %d", len(all_chunks))
    return all_chunks


async def chunk_document(document: dict) -> list[dict]:
    """
    Split a single ProcessedDocument into semantic chunks.

    Phase 1: Structural split by مادة markers.
    Phase 2: Size check per article candidate.
    Phase 3: LLM semantic split for oversized articles.

    Args:
        document: ProcessedDocument dict (keys: document_name, law_number,
                  source_file, raw_text, pages).

    Returns:
        List of Chunk dicts:
        {
            "chunk_id":      str,   # "{source_stem}::{index:04d}"
            "document_name": str,
            "law_number":    str,
            "article":       str,   # "مادة 3" — used for citation
            "section":       str,   # current chapter/section title
            "chunk_text":    str,   # text content of this chunk
            "char_count":    int,
        }
    """
    text          = document.get("raw_text", "")
    document_name = document.get("document_name", "")
    law_number    = document.get("law_number", "")
    source_stem   = document.get("source_file", "doc").replace(".pdf", "")

    if not text.strip():
        logger.warning("Empty text for document: %s", document_name)
        return []

    # ── Phase 1: structural split ──────────────────────────────────────────
    article_segments = _split_by_articles(text)

    # ── Phase 2 + 3: size check → LLM split if needed ─────────────────────
    chunks: list[dict] = []
    chunk_index = 0
    current_section = ""

    for segment in article_segments:
        seg_text = segment.strip()
        if not seg_text:
            continue

        # Track chapter / section context from structural markers
        section_match = _CHAPTER_RE.search(seg_text) or _SECTION_RE.search(seg_text)
        if section_match:
            current_section = section_match.group(1).strip()

        article_label = extract_article_number(seg_text)

        if len(seg_text) <= MAX_CHUNK_CHARS:
            # ── Phase 2: fits in one chunk ─────────────────────────────────
            chunks.append(_build_chunk(
                chunk_id      = f"{source_stem}::{chunk_index:04d}",
                chunk_text    = seg_text,
                document_name = document_name,
                law_number    = law_number,
                article       = article_label,
                section       = current_section,
            ))
            chunk_index += 1
        else:
            # ── Phase 3: too large → LLM semantic split ────────────────────
            logger.debug(
                "Article too large (%d chars), requesting LLM split: %s",
                len(seg_text), article_label,
            )
            sub_texts = await _semantic_split_with_llm(seg_text)

            for sub_text in sub_texts:
                sub_text = sub_text.strip()
                if not sub_text:
                    continue
                chunks.append(_build_chunk(
                    chunk_id      = f"{source_stem}::{chunk_index:04d}",
                    chunk_text    = sub_text,
                    document_name = document_name,
                    law_number    = law_number,
                    article       = article_label,
                    section       = current_section,
                ))
                chunk_index += 1

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# LLM Semantic Split (Phase 3)
# ─────────────────────────────────────────────────────────────────────────────

async def _semantic_split_with_llm(article_text: str) -> list[str]:
    """
    Use GPT-4o-mini to split an oversized article into semantic sub-chunks.

    Sends the article with a structured system prompt asking for JSON output.
    Falls back to paragraph splitting if:
        - LLM response is not valid JSON
        - "segments" key is missing
        - Any segment is empty

    Args:
        article_text: Single article text exceeding MAX_CHUNK_CHARS.

    Returns:
        List of 2-4 semantic text segments (or paragraph fallback).
    """
    messages = [
        SystemMessage(content=_SPLIT_SYSTEM),
        HumanMessage(content=_SPLIT_HUMAN.format(article_text=article_text)),
    ]

    try:
        response = await llm_fast.ainvoke(messages)
        raw = response.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        parsed   = json.loads(raw)
        segments = parsed.get("segments", [])

        # Validate: must be non-empty list of non-empty strings
        if isinstance(segments, list) and all(
            isinstance(s, str) and s.strip() for s in segments
        ):
            logger.debug("LLM produced %d semantic segments", len(segments))
            return segments

        logger.warning("LLM segments invalid — falling back to paragraph split")

    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("LLM split failed (%s) — falling back to paragraph split", exc)

    return _paragraph_split_fallback(article_text)


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based helpers
# ─────────────────────────────────────────────────────────────────────────────

def _split_by_articles(text: str) -> list[str]:
    """
    Split full document text into segments using مادة markers as boundaries.

    Uses re.split with a capturing group so the article header is included
    at the START of each resulting segment.

    Args:
        text: Full normalized document text.

    Returns:
        List of text segments. Each segment starts with its مادة header
        (except the first segment which may be a preamble).
    """
    parts = _ARTICLE_SPLIT_RE.split(text)

    segments: list[str] = []
    buffer = ""

    for part in parts:
        if _ARTICLE_SPLIT_RE.fullmatch(part):
            # This part is a مادة delimiter — flush buffer, start new segment
            if buffer.strip():
                segments.append(buffer.strip())
            buffer = part          # article header starts new buffer
        else:
            buffer += part         # content of current article

    if buffer.strip():
        segments.append(buffer.strip())

    # If no مادة markers found → treat whole text as one segment
    if not segments:
        segments = [text.strip()]

    return segments


def _paragraph_split_fallback(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """
    Paragraph-level fallback when LLM split fails or is unavailable.

    Splits on double newlines, merges short paragraphs until max_chars,
    and appends OVERLAP_CHARS of context at each boundary.

    Args:
        text:      Article text to split.
        max_chars: Character limit per chunk.

    Returns:
        List of sub-chunk strings.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current.strip())
            # Overlap: carry last OVERLAP_CHARS into next chunk
            current = current[-OVERLAP_CHARS:] + "\n\n" + para
        else:
            current = (current + "\n\n" + para).strip() if current else para

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text]


def extract_article_number(text: str) -> str:
    """
    Extract article label from the start of a segment for legal citation.

    Matches patterns:
        مادة 3 | مادة (3) | المادة الثالثة | ماده 5

    Args:
        text: Chunk text (article label expected near start).

    Returns:
        Matched label string (e.g. "مادة 3"), or "" if not found.
    """
    # Search only in first 80 chars — label is always at the start
    match = _ARTICLE_LABEL_RE.search(text[:80])
    if match:
        return match.group(0).strip()
    return ""


def _build_chunk(
    chunk_id:      str,
    chunk_text:    str,
    document_name: str,
    law_number:    str,
    article:       str,
    section:       str,
) -> dict:
    """
    Assemble a Chunk dict from its components.

    Args:
        chunk_id:      Unique identifier "{source_stem}::{index:04d}".
        chunk_text:    Normalized text content.
        document_name: Human-readable law name.
        law_number:    Official law number string.
        article:       Article label for citation (may be "").
        section:       Current chapter/section title (may be "").

    Returns:
        Chunk dict ready for embedder.embed_chunks().
    """
    return {
        "chunk_id":      chunk_id,
        "document_name": document_name,
        "law_number":    law_number,
        "article":       article,
        "section":       section,
        "chunk_text":    chunk_text,
        "char_count":    len(chunk_text),
    }
