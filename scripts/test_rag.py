"""
Test RAG System — Interactive CLI for testing English tax queries.

Runs the full pipeline and prints every step to terminal:
    enhance_query → retrieve → rerank → generate → result

Usage:
    python scripts/test_rag.py
    python scripts/test_rag.py --query "What is the income tax rate?"
    python scripts/test_rag.py --query "What is VAT?" --lang en
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)-35s  %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

from backend.core.database import get_readonly_session
from backend.services.rag.query_enhancer import enhance_query
from backend.services.rag.reranker import rerank_chunks
from backend.services.rag.retriever import retrieve_multi
from agents.m1.tools.tax_rag_tool import run_tax_rag, DISCLAIMER

SEP = "=" * 60


async def test_query(query: str, language: str = "en") -> None:
    print(f"\n{SEP}")
    print(f"  QUERY    : {query}")
    print(f"  LANGUAGE : {language}")
    print(SEP)

    t0 = time.perf_counter()

    # ── Step 1: Enhance (multi-query) ─────────────────────────────────────
    print("\n[ 1 / 4 ]  Enhancing query (multi-query expansion) …")
    t = time.perf_counter()
    embeddings = await enhance_query(query, language)
    print(f"           produced {len(embeddings)} embedding(s)  ({time.perf_counter()-t:.1f}s)")

    # ── Step 2: Retrieve from pgvector ────────────────────────────────────
    print("\n[ 2 / 4 ]  Retrieving from pgvector …")
    t = time.perf_counter()
    async with get_readonly_session() as db:
        chunks = await retrieve_multi(embeddings, db, top_k=5, threshold=0.50)
    print(f"           retrieved {len(chunks)} chunk(s)  ({time.perf_counter()-t:.1f}s)")

    if not chunks:
        print("\n  ⚠  No chunks above threshold — OUT OF SCOPE")
        print(f"\n  DISCLAIMER: {DISCLAIMER}\n")
        return

    print("\n  Top chunks (before rerank):")
    for i, c in enumerate(chunks[:5]):
        print(f"    [{i+1}] sim={c['similarity']:.3f}  article={c['article'] or '—'}  "
              f"law={c['law_number'] or '—'}")
        print(f"         {c['chunk_text'][:100].replace(chr(10), ' ')}…")

    # ── Step 3: Rerank ────────────────────────────────────────────────────
    print("\n[ 3 / 4 ]  Reranking chunks (GPT-4o-mini) …")
    t = time.perf_counter()
    top = await rerank_chunks(query, chunks, top_n=3)
    print(f"           kept {len(top)} chunk(s)  ({time.perf_counter()-t:.1f}s)")

    print("\n  Top chunks (after rerank):")
    for i, c in enumerate(top):
        print(f"    [{i+1}] rerank={c.get('rerank_score', 0):.1f}  "
              f"article={c['article'] or '—'}  law={c['law_number'] or '—'}")
        print(f"         {c['chunk_text'][:120].replace(chr(10), ' ')}…")

    # ── Step 4: Generate answer ───────────────────────────────────────────
    print("\n[ 4 / 4 ]  Generating answer (GPT-4o) …")
    t = time.perf_counter()
    result = await run_tax_rag(query=query, language=language)
    print(f"           done  ({time.perf_counter()-t:.1f}s)")

    # ── Final result ──────────────────────────────────────────────────────
    total = time.perf_counter() - t0
    print(f"\n{SEP}")
    print("  RESULT")
    print(SEP)
    print(f"\n  out_of_scope : {result['out_of_scope']}")
    print(f"  confidence   : {result['confidence']}")
    print(f"  sources      : {result['sources']}")

    if result["legal_reference"]:
        ref = result["legal_reference"]
        print(f"\n  legal_reference:")
        print(f"    law      : {ref['law']}")
        print(f"    article  : {ref['article']}")
        print(f"    document : {ref['document']}")

    print(f"\n  ANSWER:\n")
    print(f"  {result['answer']}")
    print(f"\n  ⚠  {result['disclaimer']}")
    print(f"\n{SEP}")
    print(f"  Total time: {total:.1f}s")
    print(SEP + "\n")


async def interactive_mode(language: str) -> None:
    print(f"\n{SEP}")
    print("  Tax RAG — Interactive Test (English)")
    print("  Type your question then Enter  |  type 'exit' to quit")
    print(SEP)

    while True:
        try:
            query = input("\n  Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting.")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            print("  Exiting.")
            break

        try:
            await test_query(query, language)
        except Exception as exc:
            print(f"\n  ERROR: {exc}\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test Tax RAG pipeline interactively.")
    parser.add_argument("--query", "-q", type=str, default=None,
                        help="Single query to test (skips interactive mode).")
    parser.add_argument("--lang", "-l", type=str, default="en",
                        choices=["en", "ar"], help="Query language (default: en).")
    return parser.parse_args()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    args = _parse_args()

    if args.query:
        asyncio.run(test_query(args.query, args.lang))
    else:
        asyncio.run(interactive_mode(args.lang))
