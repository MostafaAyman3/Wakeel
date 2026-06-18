# Sprint 4 — Advanced Tax RAG Implementation Plan

> **Status:** In Progress | **Owner:** Sprint 4 Team Member
> **Depends on:** Sprint 0 (pgvector, LLM Client, DB) + Sprint 1 (LangGraph State, RouterNode)
> **Sprint target:** Replace `tax_rag_stub` → production-ready Advanced RAG node

---

## 1. What We're Building

A **two-phase Advanced RAG system** for Egyptian tax law questions:

- **Phase A — Ingestion:** Load tax documents → chunk → embed → store in pgvector
- **Phase B — Retrieval & Reasoning:** Receive query → enhance → retrieve → rerank → generate answer with legal citation + mandatory disclaimer

### Why "Advanced" (not basic RAG)

| Basic RAG | Advanced RAG (what we're building) |
|-----------|-----------------------------------|
| Embed query → retrieve → answer | HyDE query enhancement → multi-query → retrieve → rerank → answer |
| No confidence filtering | Reject out-of-scope questions if similarity < 0.75 |
| No source citation | Always cites legal article + document name |
| Fixed chunks | Semantic chunking with Arabic-aware splitting |

---

## 2. Current State (Sprint 0 + 1 Done)

### Already exists — do NOT rebuild:
- `agents/shared/llm_client.py` → `llm_primary` (GPT-4o), `embeddings` (text-embedding-3-small, dim=1536)
- `backend/core/config.py` → `tax_docs_path`, `rag_top_k=5`, `rag_similarity_threshold=0.75`, `vector_embedding_dimension=1536`
- `agents/m1/schemas/m1_state.py` → `M1State` with `raw_data`, `narrative`, `final_response`
- `agents/m1/graphs/m1_graph.py` → `tax_rag_stub` waiting to be replaced
- `agents/m1/nodes/stub_nodes.py` → `tax_rag_stub` function

### Placeholders to implement:
- `agents/m1/tools/tax_rag_tool.py` → currently a docstring comment
- `backend/services/rag_service.py` → currently a docstring comment

---

## 3. Files to Create / Modify

```
data/
  tax_knowledge_base/                    ← NEW: 3-5 Arabic tax law text files

scripts/
  ingest_tax_docs.py                     ← NEW: one-time ingestion script (CLI)

backend/
  models/
    tax_chunk.py                         ← NEW: SQLAlchemy pgvector model
  services/
    rag_service.py                       ← IMPLEMENT (currently placeholder)

agents/
  m1/
    nodes/
      tax_rag_node.py                    ← NEW: real node (replaces stub)
    tools/
      tax_rag_tool.py                    ← IMPLEMENT (currently placeholder)
    graphs/
      m1_graph.py                        ← MODIFY: swap stub → real node
    tests/
      test_tax_rag.py                    ← NEW: unit + integration tests
```

---

## 4. Database Schema — pgvector Table

```sql
-- Enable pgvector (already done in Sprint 0)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE tax_chunks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id      TEXT NOT NULL UNIQUE,          -- doc_name::chunk_index
    document_name TEXT NOT NULL,                 -- "قانون الضريبة على القيمة المضافة"
    law_number    TEXT,                          -- "القانون رقم 67 لسنة 2016"
    article       TEXT,                          -- "المادة 3"
    section       TEXT,                          -- chapter / section title
    chunk_text    TEXT NOT NULL,
    embedding     VECTOR(1536) NOT NULL,
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ANN index for fast similarity search
CREATE INDEX tax_chunks_embedding_idx
    ON tax_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

## 5. Advanced RAG Architecture

```
User Query (AR/EN: tax question)
         │
         ▼
┌────────────────────────────────────────────────────┐
│             PHASE 1: Query Enhancement             │
│  ┌─────────────────────────────────────────────┐  │
│  │  HyDE: GPT-4o-mini generates a hypothetical │  │
│  │  answer → embed it for better retrieval     │  │
│  └─────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────┐  │
│  │  Multi-Query: GPT-4o-mini generates 3       │  │
│  │  query variations → retrieve for each       │  │
│  └─────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
         │  (3 + 1 enhanced queries)
         ▼
┌────────────────────────────────────────────────────┐
│           PHASE 2: Retrieval from pgvector         │
│  top_k=5 per query → deduplicate → up to 15 chunks │
│  Filter: similarity_score >= 0.75                  │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│           PHASE 3: Reranking                       │
│  GPT-4o-mini scores each chunk (0-10) for          │
│  relevance to original query → top 3 selected      │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│     Out-of-Scope Guard                             │
│  If max_score < 0.75 → return "لا يمكنني           │
│  الإجابة خارج نطاق القواعد المتاحة"                 │
└────────────────────────────────────────────────────┘
         │ (in-scope only)
         ▼
┌────────────────────────────────────────────────────┐
│           PHASE 4: Generation (GPT-4o)             │
│  System: tax advisor role + disclaimer mandate     │
│  Context: top 3 reranked chunks                    │
│  Output: { answer, legal_reference, disclaimer }   │
└────────────────────────────────────────────────────┘
```

---

## 6. Key Techniques Explained

### 6.1 HyDE (Hypothetical Document Embeddings)
Instead of embedding the raw question (which may not match legal text well), we ask GPT-4o-mini to generate a *hypothetical tax law answer*, then embed that. This makes the embedding closer to what a real legal document looks like.

```python
hyde_prompt = f"أكتب إجابة قانونية مختصرة لسؤال ضريبي: {query}"
hypothetical_answer = await llm_fast.ainvoke(hyde_prompt)
hyde_embedding = await embeddings.aembed_query(hypothetical_answer)
```

### 6.2 Multi-Query Retrieval
Generate 3 Arabic/English variations of the query to maximize recall from different phrasings in the legal documents.

```python
variations = ["نسخة عربية مختلفة 1", "نسخة عربية مختلفة 2", "English version"]
# Retrieve top_k for each → deduplicate by chunk_id
```

### 6.3 LLM Reranking
After retrieval, ask GPT-4o-mini to score each chunk 0–10 for relevance. Select top 3. This is cheaper than cross-encoder models and works well for Arabic.

### 6.4 Out-of-Scope Guard
If all retrieved chunks have cosine similarity < 0.75, the question is outside the knowledge base. Return a structured refusal — never hallucinate.

---

## 7. Response Schema

```python
TaxRAGResponse = {
    "answer": str,              # The actual legal answer
    "legal_reference": {
        "law": str,             # "القانون رقم 67 لسنة 2016"
        "article": str,         # "المادة 3، الفقرة 2"
        "document": str,        # document_name from tax_chunks
    },
    "confidence": float,        # Max similarity score from retrieval
    "sources": list[str],       # List of chunk_ids used
    "disclaimer": str,          # MANDATORY, always included
    "out_of_scope": bool,       # True if refused to answer
}

DISCLAIMER = "توجيه استرشادي — استشر مستشاراً ضريبياً للقرارات الرسمية"
```

---

## 8. Integration with LangGraph (m1_graph.py)

The `tax_rag_stub` in the graph gets replaced with `tax_rag_node`:

```python
# BEFORE (Sprint 1 stub):
from agents.m1.nodes.stub_nodes import tax_rag_stub
graph.add_node("tax_rag_stub", tax_rag_stub)

# AFTER (Sprint 4 real node):
from agents.m1.nodes.tax_rag_node import tax_rag_node
graph.add_node("tax_rag_node", tax_rag_node)
```

The node reads `state["query"]` and `state["extracted_params"]`, runs the full RAG pipeline, and writes to `state["raw_data"]`, `state["narrative"]`, `state["final_response"]`.

---

## 9. Tax Knowledge Base Content (3-5 Documents)

For the MVP, create `.txt` files with structured Egyptian tax law content:

| File | Content | Articles |
|------|---------|---------|
| `vat_law_67_2016.txt` | قانون الضريبة على القيمة المضافة رقم 67/2016 | أساس الضريبة، الإعفاءات، نسبة 14% |
| `income_tax_law_91_2005.txt` | قانون ضريبة الدخل رقم 91/2005 | ضريبة الدخل على الأفراد والشركات |
| `stamp_duty_law.txt` | قانون الدمغة | أنواع الدمغة وقيمها |
| `real_estate_tax.txt` | ضريبة العقارات المبنية | حساب الضريبة، الإعفاءات |
| `withholding_tax.txt` | ضريبة الخصم والإضافة | المعدلات والحالات |

Each document must be structured with clear article references for citation.

---

## 10. Testing Requirements

| Test | Description | Expected |
|------|-------------|---------|
| `test_in_scope_arabic` | سؤال عن نسبة VAT | إجابة + مرجع قانوني + disclaimer |
| `test_in_scope_english` | "What is the VAT rate?" | Answer + reference + disclaimer |
| `test_out_of_scope` | "ما هو حكم الطلاق؟" | out_of_scope=True, no answer |
| `test_low_confidence` | سؤال ذو صلة ضعيفة | out_of_scope=True |
| `test_disclaimer_mandatory` | أي سؤال ضريبي | disclaimer موجود دائماً |
| `test_source_citation` | أي سؤال ضريبي | legal_reference غير فارغ |
| `test_stub_replaced` | m1_graph imports | لا يوجد tax_rag_stub في الـ graph |

---

## 11. Dependencies to Add

```txt
# في agents/requirements.txt
langchain-community       # Document loaders
pgvector                  # pgvector Python client
sqlalchemy[asyncio]       # already there via Sprint 0
asyncpg                   # async PostgreSQL driver
```

---

## 12. Environment Variables (موجودة بالفعل في config.py)

```env
TAX_DOCS_PATH=./data/tax_knowledge_base
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.75
VECTOR_EMBEDDING_DIMENSION=1536
```

لا تحتاج إضافة حاجة جديدة — كل الـ settings موجودة من Sprint 0.

---

## 13. What is NOT in Sprint 4 Scope

- ❌ PDF parsing / OCR (المستندات نصية `.txt` فقط في MVP)
- ❌ Real-time tax law updates
- ❌ Fine-tuned embedding model
- ❌ Cross-encoder reranking (نستخدم GPT-4o-mini بدلاً منه)
- ❌ UI for the RAG (Sprint 6 scope)
