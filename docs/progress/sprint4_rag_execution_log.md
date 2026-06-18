# Sprint 4 — Tax RAG System Execution Log

> Documents all implementation work done for M1-Sprint 4 (Tax Knowledge RAG).
> Read this alongside `agent_execution_log.md` (Steps 1-17) for full project context.

---

## Step 18

Time: 2026-06-16
Action: Implemented M1-Sprint 4 — Tax RAG System (full pipeline: ingest → chunk → embed → retrieve → rerank → generate)
Reason: Sprint 4 deliverable — "Load tax documents → chunk + embed → pgvector → tax_rag_tool.py with disclaimer"

Files created/updated:
- `backend/services/rag/pdf_loader.py` — PDF/text loader + Arabic normalization
- `backend/services/rag/chunker.py` — Hierarchical semantic chunker (3-phase)
- `backend/services/rag/embedder.py` — Chunk embedding + pgvector upsert
- `backend/services/rag/query_enhancer.py` — HyDE + multi-query expansion
- `backend/services/rag/retriever.py` — pgvector cosine similarity search + deduplication
- `backend/services/rag/reranker.py` — LLM-based chunk reranking (GPT-4o-mini)
- `agents/m1/tools/tax_rag_tool.py` — Full RAG pipeline orchestrator
- `agents/m1/nodes/tax_rag_node.py` — LangGraph node wrapping tax_rag_tool
- `scripts/ingest_tax_docs.py` — One-time ingestion CLI (modified to load .txt from processed/)
- `data/tax_knowledge_base/processed/قانون رقم 91 لسنة 2005 بإصدار قانون الضريبة على الدخل.txt` — manually prepared
- `data/tax_knowledge_base/processed/إصدار قانون الإجراءات الضريبية الموحد.txt` — manually prepared

---

## Pipeline Architecture

### Ingestion (one-time, run before app starts)

```
scripts/ingest_tax_docs.py
    → pdf_loader.load_all_processed_texts()     # read .txt from processed/
    → chunker.chunk_all_documents()              # Phase 1: مادة split
                                                 # Phase 2: size gate (1800 chars)
                                                 # Phase 3: GPT-4o-mini semantic split
    → embedder.embed_chunks()                    # text-embedding-3-small, batches of 50
    → embedder.store_chunks()                    # upsert → tax_chunks (pgvector VECTOR(1536))
```

### Query Time (per user request)

```
tax_rag_node (LangGraph)
    → tax_rag_tool.run_tax_rag()
        → query_enhancer.enhance_query()         # normalize → HyDE → 3 variations (concurrent)
        → retriever.retrieve_multi()             # cosine search per embedding, dedup by chunk_id
        → reranker.rerank_chunks()              # GPT-4o-mini scores 0-10 per chunk → top 3
        → llm_primary (GPT-4o)                  # generate grounded answer from context only
        → return TaxRAGResult
    → writes to M1State:
        raw_data, data_confidence, narrative, output_format, final_response
```

---

## Key Decisions

| Decision | Choice | Reason |
|---|---|---|
| Document source | `processed/` .txt files (manual copy-paste) | PDFs had encoding issues; manual text is cleaner |
| Arabic fix for copy-pasted text | `line[::-1]` + `unicodedata.normalize('NFKC')` | Presentation forms stored in visual (reversed) order; NFKC converts to base Unicode. `arabic_reshaper` alone keeps presentation forms — wrong for copy-pasted input |
| Chunk size limit | MAX_CHUNK_CHARS = 1800 (~450 Arabic tokens) | Balances context window and semantic coherence |
| Oversized articles | GPT-4o-mini semantic split (Phase 3) | Fixed-size splitting breaks legal context mid-sentence |
| Query enhancement | HyDE + 3 variations, all concurrent | Bridges colloquial Egyptian Arabic to formal MSA law text |
| Similarity threshold | 0.75 cosine | Below this → out_of_scope, no hallucination |
| Reranking | GPT-4o-mini 0-10 score | Cosine similarity ≠ legal relevance; LLM understands Arabic legal context |
| Disclaimer | Always included | Mandatory — every response regardless of out_of_scope |
| pgvector upsert | ON CONFLICT (chunk_id) DO UPDATE | Ingestion script safe to re-run with or without --clear |
| Graph position | RouterNode → tax_rag_node → ValidationEnrichmentNode → END | Replaces tax_rag_stub in stub_nodes.py |

---

## Module Responsibilities

### `pdf_loader.py`
- `load_processed_txt()` — loads a single .txt file, applies Arabic presentation-form fix + normalization
- `load_all_processed_texts()` — batch loads all .txt files from `processed/`
- `normalize_arabic()` — removes tashkeel, unifies alef/teh marbuta/alef maqsura, collapses whitespace
- `extract_document_metadata()` — parses law number + document name from content or filename
- `load_pdf()` / `load_all_pdfs()` — original PDF path (kept, not used in current pipeline)
- `save_processed_text()` — saves extracted text with structured header to processed/

### `chunker.py`
- `chunk_all_documents()` — entry point, returns flat list of Chunk dicts
- `chunk_document()` — 3-phase pipeline per document
- `_split_by_articles()` — regex split on مادة/ماده markers
- `_semantic_split_with_llm()` — GPT-4o-mini splits oversized articles into 2-4 segments
- `_paragraph_split_fallback()` — fallback when LLM fails, uses double-newline boundaries + overlap

### `embedder.py`
- `embed_chunks()` — batched OpenAI embedding (text-embedding-3-small, BATCH_SIZE=50)
- `store_chunks()` — upsert to tax_chunks with pgvector string format `[f1,f2,…]`
- `clear_all_chunks()` — DELETE all rows (used with --clear flag)
- `count_chunks()` — current row count

### `query_enhancer.py`
- `enhance_query()` — full pipeline: normalize → HyDE + variations concurrently → batch embed
- `generate_hyde_embedding()` — GPT-4o-mini generates MSA legal answer → embed it
- `generate_query_variations()` — 3 variations: formal AR, synonym AR, EN/AR translation
- `normalize_arabic_query()` — same normalization as pdf_loader (ensures query/chunk parity)

### `retriever.py`
- `retrieve()` — single embedding cosine search with threshold + top_k
- `retrieve_multi()` — concurrent search across all embeddings → deduplicate by chunk_id
- `deduplicate_chunks()` — keeps highest similarity score per chunk_id

### `reranker.py`
- `rerank_chunks()` — GPT-4o-mini scores each chunk 0-10 → returns top_n
- `build_rerank_prompt()` — formats chunks with article/law prefix (350 chars preview each)
- `parse_rerank_scores()` — JSON parsing with fallback to uniform 5.0 scores

### `tax_rag_tool.py`
- `run_tax_rag()` — orchestrates full 7-step RAG pipeline
- `_generate_answer()` — GPT-4o generates answer grounded in context only
- `_build_context()` — formats top chunks with article/law citation headers
- `_build_legal_reference()` — extracts structured { law, article, document } from top chunk
- `_out_of_scope_result()` — standardised refusal response (disclaimer always included)

### `tax_rag_node.py`
- `tax_rag_node()` — LangGraph node: reads M1State → calls run_tax_rag() → writes state fields
- `_error_state()` — safe error fallback that keeps graph moving without crashing

---

## TaxRAGResult Schema

```python
{
    "answer":          str,          # GPT-4o generated answer (grounded in context)
    "legal_reference": {             # from top reranked chunk (or None)
        "law":      str,             # e.g. "القانون رقم 91 لسنة 2005"
        "article":  str,             # e.g. "مادة 3"
        "document": str,             # document_name
    } | None,
    "confidence":      float,        # rerank_score / 10 normalised to [0.0, 1.0]
    "sources":         list[str],    # chunk_ids used as context
    "disclaimer":      str,          # ALWAYS: "توجيه استرشادي — استشر مستشاراً ضريبياً للقرارات الرسمية"
    "out_of_scope":    bool,         # True if no chunks passed similarity threshold
}
```

---

## Document Status

| File | Format | Status |
|---|---|---|
| قانون رقم 91 لسنة 2005 بإصدار قانون الضريبة على الدخل.txt | Clean Arabic Unicode | Ready ✓ |
| إصدار قانون الإجراءات الضريبية الموحد.txt | Arabic presentation forms (NFKC fix applied) | Ready ✓ |

---

## Sprint 4 Checklist

- [x] Load tax rule documents into `data/tax_knowledge_base/` — 2 documents in `processed/`
- [x] Implement `pdf_loader.py` — text loading + Arabic normalization
- [x] Implement `chunker.py` — 3-phase hierarchical semantic chunking
- [x] Implement `embedder.py` — batched embedding + pgvector upsert
- [x] Implement `query_enhancer.py` — HyDE + multi-query expansion
- [x] Implement `retriever.py` — cosine search + deduplication
- [x] Implement `reranker.py` — LLM reranking
- [x] Implement `tax_rag_tool.py` — full pipeline orchestrator with disclaimer
- [x] Implement `tax_rag_node.py` — LangGraph node (replaces tax_rag_stub)
- [x] Modify `ingest_tax_docs.py` — load from processed/ .txt instead of raw/ PDFs
- [ ] Run full ingestion: `python scripts/ingest_tax_docs.py` — **PENDING** (embed + store to pgvector)
- [ ] Wire tax_rag_node into m1_graph.py replacing stub

---

## To Run Ingestion

```bash
# Dry run first (no DB write, shows chunk count + sample)
python scripts/ingest_tax_docs.py --dry-run

# Full ingestion
python scripts/ingest_tax_docs.py

# Re-ingest from scratch (wipe and reload)
python scripts/ingest_tax_docs.py --clear
```

Result: SUCCESS — Sprint 4 RAG infrastructure COMPLETE. Ingestion to pgvector pending.
