"""
Ingest Tax Documents — One-Time CLI Script.

Purpose:
    Load Arabic tax law PDFs → extract text → chunk → embed → store in pgvector.
    Run this ONCE before starting the application, or with --clear to re-ingest.

Pipeline:
    pdf_loader.load_all_pdfs()
        → chunker.chunk_all_documents()
        → embedder.embed_chunks()
        → embedder.store_chunks()

Usage:
    python scripts/ingest_tax_docs.py
    python scripts/ingest_tax_docs.py --clear      # wipe and re-ingest all
    python scripts/ingest_tax_docs.py --dry-run    # show chunk count, no DB write

Expected output:
    Loaded   3 PDF documents
    Generated 87 chunks
    Embedded  87 chunks  (batches of 100)
    Stored    87 chunks in pgvector ✓

Source directory:  data/tax_knowledge_base/raw/     (PDFs)
Output directory:  data/tax_knowledge_base/processed/ (extracted .txt files)
Database table:    tax_chunks                         (pgvector)

Dependencies (must be installed):
    PyMuPDF (fitz)  — pip install pymupdf
    pgvector        — pip install pgvector
    asyncpg         — pip install asyncpg

Config read from .env via backend.core.config:
    TAX_DOCS_PATH            = ./data/tax_knowledge_base
    VECTOR_EMBEDDING_DIMENSION = 1536
    OPENAI_API_KEY           = ...
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# ── Make sure project root is on sys.path ──────────────────────────────────────
# Needed when running: python scripts/ingest_tax_docs.py from the project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.config import get_settings
from backend.core.database import get_db_session
from backend.services.rag.chunker import chunk_all_documents
from backend.services.rag.embedder import clear_all_chunks, count_chunks, embed_chunks, store_chunks
from backend.services.rag.pdf_loader import load_all_pdfs, save_processed_text

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

async def run_ingestion(clear: bool = False, dry_run: bool = False) -> None:
    settings   = get_settings()
    base_path  = Path(settings.tax_docs_path)
    raw_dir    = base_path / "raw"
    proc_dir   = base_path / "processed"

    proc_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 55)
    print("  Tax Document Ingestion Pipeline")
    print("=" * 55)
    if dry_run:
        print("  MODE: DRY RUN — no data will be written to the DB")
    if clear:
        print("  MODE: CLEAR — existing chunks will be deleted first")
    print(f"  Source : {raw_dir}")
    print(f"  Output : {proc_dir}")
    print("=" * 55 + "\n")

    t_start = time.perf_counter()

    # ── Step 1: Load PDFs ─────────────────────────────────────────────────
    print("[ 1 / 4 ]  Loading PDFs …")
    documents = load_all_pdfs(raw_dir)

    if not documents:
        print(f"\n  ERROR: No PDFs found in {raw_dir}")
        print("  Put your Arabic tax law PDFs there and re-run.\n")
        sys.exit(1)

    print(f"           Loaded {len(documents)} document(s)")
    for doc in documents:
        print(f"           • {doc['source_file']}  ({doc['pages']} pages)")

    # Save extracted .txt files for inspection
    for doc in documents:
        save_processed_text(doc, proc_dir)

    # ── Step 2: Chunk ─────────────────────────────────────────────────────
    print(f"\n[ 2 / 4 ]  Chunking {len(documents)} document(s) …")
    chunks = await chunk_all_documents(documents)

    if not chunks:
        print("\n  ERROR: Chunker produced 0 chunks — check your PDFs.\n")
        sys.exit(1)

    print(f"           Generated {len(chunks)} chunk(s)")

    # ── Dry-run exit ──────────────────────────────────────────────────────
    if dry_run:
        _print_chunk_sample(chunks)
        elapsed = time.perf_counter() - t_start
        print(f"\n  DRY RUN complete in {elapsed:.1f}s — nothing written to DB.\n")
        return

    # ── Step 3: Embed ─────────────────────────────────────────────────────
    print(f"\n[ 3 / 4 ]  Embedding {len(chunks)} chunk(s) via text-embedding-3-small …")
    embedded = await embed_chunks(chunks)
    print(f"           Embedded {len(embedded)} chunk(s)  ✓")

    # ── Step 4: Store in pgvector ─────────────────────────────────────────
    print(f"\n[ 4 / 4 ]  Storing in pgvector …")
    async with get_db_session() as db:
        if clear:
            deleted = await clear_all_chunks(db)
            print(f"           Cleared {deleted} existing chunk(s)")

        stored = await store_chunks(embedded, db)
        total  = await count_chunks(db)

    print(f"           Stored  {stored} chunk(s)  ✓")
    print(f"           Total in tax_chunks table: {total}")

    # ── Summary ───────────────────────────────────────────────────────────
    elapsed = time.perf_counter() - t_start
    print("\n" + "=" * 55)
    print("  Ingestion complete")
    print(f"  Documents : {len(documents)}")
    print(f"  Chunks    : {stored}")
    print(f"  Time      : {elapsed:.1f}s")
    print("=" * 55 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _print_chunk_sample(chunks: list[dict], n: int = 3) -> None:
    """Print the first n chunks for dry-run inspection."""
    print(f"\n  Sample chunks (first {min(n, len(chunks))}):")
    for i, chunk in enumerate(chunks[:n]):
        law     = chunk.get("law_number", "—")
        article = chunk.get("article",    "—")
        preview = chunk.get("chunk_text", "")[:120].replace("\n", " ")
        print(f"\n  [{i + 1}] law={law}  article={article}")
        print(f"       {preview}…")


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Arabic tax PDFs into the pgvector knowledge base.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/ingest_tax_docs.py                 # normal ingest
  python scripts/ingest_tax_docs.py --dry-run       # count chunks, no DB write
  python scripts/ingest_tax_docs.py --clear         # wipe DB then re-ingest
        """,
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete all existing chunks before ingesting (full re-index).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run load + chunk only — do not embed or write to the database.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Windows ProactorEventLoop has SSL issues with asyncpg — use SelectorEventLoop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = _parse_args()
    asyncio.run(run_ingestion(clear=args.clear, dry_run=args.dry_run))
