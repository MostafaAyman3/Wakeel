"""
PDF Loader — Arabic PDF extraction and text cleaning.

Responsibility:
    - Extract text from Arabic PDFs using PyMuPDF (fitz)
    - Fix RTL ordering issues common in Arabic PDFs
    - Normalize Arabic characters (remove tashkeel, unify alef forms)
    - Parse document metadata from filename and content headers
    - Save processed text to data/tax_knowledge_base/processed/

Input:
    PDF files from data/tax_knowledge_base/raw/

Output:
    List of ProcessedDocument dicts:
    {
        "document_name": str,   # e.g. "قانون الضريبة على القيمة المضافة"
        "law_number":    str,   # e.g. "القانون رقم 67 لسنة 2016"
        "source_file":   str,   # original PDF filename
        "raw_text":      str,   # full extracted + normalized text
        "pages":         int,   # page count
    }

Library: PyMuPDF (fitz) — chosen for best Arabic RTL support
NOT: pypdf, pdfminer (poor Arabic encoding handling)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import arabic_reshaper
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Arabic Presentation Forms: U+FE70–U+FEFF (isolated/medial/final glyph forms)
# PDFs that use these store characters in visual order (right→left on screen
# = left→right in memory). Both character order AND word order are reversed.
_PRES_FORMS = re.compile(r"[ﹰ-﻿ﭐ-﷿]")


def _fix_arabic_text(text: str) -> str:
    """
    Fix Arabic text from PDFs that store glyphs in visual (reversed) order.

    Problem: these PDFs write each line's characters left-to-right in memory
             but the characters appear right-to-left on screen — so both
             character order and word order are reversed.

    Fix (per line):
        1. line[::-1]               — reverse character sequence → logical order
        2. arabic_reshaper.reshape()— connect characters properly (ﺟ → ج)

    Only lines containing Presentation Form characters are processed.
    Latin / numeric lines pass through unchanged.
    """
    if not _PRES_FORMS.search(text):
        return text

    try:
        lines  = text.split("\n")
        fixed  = []
        for line in lines:
            if _PRES_FORMS.search(line):
                # Step 1: reverse (visual → logical), Step 2: reshape
                fixed.append(arabic_reshaper.reshape(line[::-1]))
            else:
                fixed.append(line)
        return "\n".join(fixed)
    except Exception as exc:
        logger.warning("_fix_arabic_text failed: %s — using raw text", exc)
        return text


# ── Arabic Unicode ranges ──────────────────────────────────────────────────────
# Full tashkeel block: Quran marks + standard diacritics + extended
_TASHKEEL = re.compile(
    r"[ؐ-ًؚ-ٟۖ-ۜ۟-۪ۤۧۨ-ۭ]"
)
_ALEF     = re.compile(r"[أإآٱ]")        # Alef with hamza / madda / wasla → bare Alef
_TEH_MARB = re.compile(r"ة")             # Teh Marbuta → Heh
_YEH      = re.compile(r"ى")             # Alef Maqsura → Yeh
_MULTI_NL = re.compile(r"\n{3,}")        # 3+ consecutive newlines → 2
_MULTI_SP = re.compile(r"[ \t]+")        # Multiple spaces/tabs → single space

# ── Law number patterns (Arabic) ───────────────────────────────────────────────
_LAW_NUM_PATTERN = re.compile(
    r"(?:القانون|قانون)\s+رقم\s+\d+\s+لسنه\s+\d+"
    r"|(?:القانون|قانون)\s+رقم\s+\d+\s+لسنة\s+\d+",
    re.UNICODE,
)

# ── Structured file headers (used in manually prepared .txt exports) ───────────
_DOC_HEADER = re.compile(r"^DOCUMENT:\s*(.+)$", re.MULTILINE)
_LAW_HEADER = re.compile(r"^LAW_NUMBER:\s*(.+)$", re.MULTILINE)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_pdf(file_path: str) -> dict:
    """
    Extract and clean text from a single Arabic PDF file.

    Uses PyMuPDF page.get_text("text", sort=True) for correct RTL reading order.
    Each page is extracted separately then joined with double newlines.

    Args:
        file_path: Absolute or relative path to the PDF file.

    Returns:
        ProcessedDocument dict:
        {
            "document_name": str,
            "law_number":    str,
            "source_file":   str,   # just the filename, not full path
            "raw_text":      str,   # normalized full text
            "pages":         int,
        }

    Raises:
        FileNotFoundError: If the PDF path does not exist.
        RuntimeError:      If PyMuPDF fails to open the file.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    logger.info("Loading PDF: %s", path.name)

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        raise RuntimeError(f"PyMuPDF failed to open {path.name}: {exc}") from exc

    pages_text: list[str] = []

    for page in doc:
        # sort=True → PyMuPDF reorders text blocks top-to-bottom, left-to-right
        # For Arabic RTL this still produces correct paragraph order per page.
        page_text = page.get_text("text", sort=True)
        if page_text.strip():
            pages_text.append(_fix_arabic_text(page_text))

    doc.close()

    raw_text       = "\n\n".join(pages_text)
    normalized     = normalize_arabic(raw_text)
    metadata       = extract_document_metadata(normalized, path.name)

    result = {
        "document_name": metadata["document_name"],
        "law_number":    metadata["law_number"],
        "source_file":   path.name,
        "raw_text":      normalized,
        "pages":         len(pages_text),
    }

    logger.info(
        "  ✓ %s — %d pages, %d chars",
        path.name, result["pages"], len(normalized),
    )
    return result


def load_all_pdfs(raw_dir: str) -> list[dict]:
    """
    Load all PDF files from the raw directory.

    Iterates over *.pdf files alphabetically. Logs a warning but continues
    if a single file fails, so one bad PDF never blocks the rest.

    Args:
        raw_dir: Path to data/tax_knowledge_base/raw/

    Returns:
        List of ProcessedDocument dicts (one per successfully loaded PDF).
    """
    raw_path = Path(raw_dir)

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw directory not found: {raw_dir}")

    pdf_files = sorted(raw_path.glob("*.pdf"))

    if not pdf_files:
        logger.warning("No PDF files found in %s", raw_dir)
        return []

    logger.info("Found %d PDF files in %s", len(pdf_files), raw_dir)

    documents: list[dict] = []
    for pdf_path in pdf_files:
        try:
            doc = load_pdf(str(pdf_path))
            documents.append(doc)
        except Exception as exc:
            logger.error("  ✗ Skipping %s: %s", pdf_path.name, exc)

    logger.info("Loaded %d / %d documents successfully", len(documents), len(pdf_files))
    return documents


# ─────────────────────────────────────────────────────────────────────────────
# Text normalization
# ─────────────────────────────────────────────────────────────────────────────

def normalize_arabic(text: str) -> str:
    """
    Normalize Arabic text for consistent embedding and retrieval.

    All normalization steps are also applied in query_enhancer.normalize_arabic_query()
    so that stored chunk text and query text share the same representation.

    Operations (in order):
        1. Remove tashkeel (diacritics / Quranic marks)
        2. Unify Alef forms: أ إ آ ٱ → ا
        3. Unify Teh Marbuta: ة → ه
        4. Unify Alef Maqsura: ى → ي
        5. Collapse multiple spaces / tabs → single space
        6. Collapse 3+ newlines → 2 newlines (preserve paragraph breaks)
        7. Strip leading / trailing whitespace

    Args:
        text: Raw Arabic text extracted from PDF.

    Returns:
        Normalized text string.
    """
    text = _TASHKEEL.sub("", text)
    text = _ALEF.sub("ا", text)
    text = _TEH_MARB.sub("ه", text)
    text = _YEH.sub("ي", text)
    text = _MULTI_SP.sub(" ", text)
    text = _MULTI_NL.sub("\n\n", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Metadata extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_document_metadata(text: str, filename: str) -> dict:
    """
    Parse law number and document name from text content or filename.

    Priority order:
        1. Structured headers (DOCUMENT: / LAW_NUMBER:) — manually prepared files
        2. Law number pattern in first 600 chars of text  — "القانون رقم X لسنة Y"
        3. Law number pattern in filename
        4. Filename stem (cleaned) as document name fallback

    Args:
        text:     Normalized extracted text from the PDF.
        filename: Original PDF filename (e.g. "القيمة المضافة1.pdf").

    Returns:
        {"document_name": str, "law_number": str}
        Empty strings if not found (never raises).
    """
    document_name = ""
    law_number    = ""

    # ── 1. Structured DOCUMENT: / LAW_NUMBER: headers ─────────────────────────
    doc_match = _DOC_HEADER.search(text)
    if doc_match:
        document_name = doc_match.group(1).strip()

    law_header_match = _LAW_HEADER.search(text)
    if law_header_match:
        law_number = law_header_match.group(1).strip()

    # ── 2. Law number from first 600 chars of text ─────────────────────────────
    if not law_number:
        law_match = _LAW_NUM_PATTERN.search(text[:600])
        if law_match:
            law_number = law_match.group(0).strip()

    # ── 3. Law number from filename ────────────────────────────────────────────
    if not law_number:
        law_match = _LAW_NUM_PATTERN.search(filename)
        if law_match:
            law_number = law_match.group(0).strip()

    # ── 4. Document name from filename (fallback) ──────────────────────────────
    if not document_name:
        stem = Path(filename).stem              # strip .pdf
        stem = re.sub(r"\s*\d+$", "", stem)    # strip trailing digits: "VAT 2" → "VAT"
        document_name = stem.strip()

    return {
        "document_name": document_name,
        "law_number":    law_number,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Persistence
# ─────────────────────────────────────────────────────────────────────────────

def save_processed_text(document: dict, processed_dir: str) -> str:
    """
    Save a ProcessedDocument's normalized text to processed/ as a .txt file.

    File format:
        DOCUMENT: <document_name>
        LAW_NUMBER: <law_number>
        SOURCE_FILE: <source_file>
        PAGES: <pages>
        ────────────────────────────────────────────────────────────
        <normalized text body>

    The metadata header is written so that if the .txt file is ever
    re-loaded (e.g. for re-chunking without re-extracting the PDF),
    extract_document_metadata() can parse it via the DOCUMENT: pattern.

    Args:
        document:      ProcessedDocument dict (must have all 5 keys).
        processed_dir: Path to data/tax_knowledge_base/processed/

    Returns:
        Absolute path to the saved .txt file.
    """
    processed_path = Path(processed_dir)
    processed_path.mkdir(parents=True, exist_ok=True)

    stem        = Path(document["source_file"]).stem   # filename without .pdf
    output_file = processed_path / f"{stem}.txt"

    header = (
        f"DOCUMENT: {document['document_name']}\n"
        f"LAW_NUMBER: {document['law_number']}\n"
        f"SOURCE_FILE: {document['source_file']}\n"
        f"PAGES: {document['pages']}\n"
        f"{'─' * 60}\n\n"
    )

    output_file.write_text(header + document["raw_text"], encoding="utf-8")

    logger.info("Saved → %s (%d chars)", output_file.name, len(document["raw_text"]))
    return str(output_file)
