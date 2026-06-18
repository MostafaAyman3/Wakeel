# Sprint 4 — Step-by-Step Implementation Tracker

> اتبع الخطوات بالترتيب. كل خطوة لها: ما تعمله، الملفات المتأثرة، وكيف تتحقق إنها شغالة.

---

## الخطوة 1 — إنشاء جدول pgvector في DB
**الهدف:** إنشاء جدول `tax_chunks` بـ VECTOR column لتخزين الـ embeddings

### الملفات:
- **إنشاء:** `backend/models/tax_chunk.py`
- **إنشاء:** `scripts/create_tax_table.sql` (أو migration)

### المحتوى المطلوب في `backend/models/tax_chunk.py`:
```python
"""SQLAlchemy model for tax knowledge base chunks stored in pgvector."""

import uuid
from datetime import datetime
from sqlalchemy import Column, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from backend.core.database import Base

class TaxChunk(Base):
    __tablename__ = "tax_chunks"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id      = Column(Text, nullable=False, unique=True)   # doc_name::index
    document_name = Column(Text, nullable=False)
    law_number    = Column(Text)
    article       = Column(Text)
    section       = Column(Text)
    chunk_text    = Column(Text, nullable=False)
    embedding     = Column(Vector(1536), nullable=False)
    metadata_     = Column("metadata", JSONB, default={})
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
```

### SQL للتنفيذ مباشرة على DB:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tax_chunks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id      TEXT NOT NULL UNIQUE,
    document_name TEXT NOT NULL,
    law_number    TEXT,
    article       TEXT,
    section       TEXT,
    chunk_text    TEXT NOT NULL,
    embedding     VECTOR(1536) NOT NULL,
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS tax_chunks_embedding_idx
    ON tax_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### التحقق ✓:
```sql
SELECT table_name FROM information_schema.tables WHERE table_name = 'tax_chunks';
-- يجب أن يرجع: tax_chunks
```

---

## الخطوة 2 — إنشاء قاعدة المعرفة الضريبية (Tax Knowledge Base)
**الهدف:** إنشاء مجلد `data/tax_knowledge_base/` مع 3-5 ملفات نصية بمحتوى قانوني ضريبي منظم

### الملفات:
- **إنشاء:** `data/tax_knowledge_base/vat_law_67_2016.txt`
- **إنشاء:** `data/tax_knowledge_base/income_tax_law_91_2005.txt`
- **إنشاء:** `data/tax_knowledge_base/withholding_tax.txt`

### هيكل كل ملف (مهم للـ citation):
```
DOCUMENT: قانون الضريبة على القيمة المضافة
LAW_NUMBER: القانون رقم 67 لسنة 2016
SOURCE: الجريدة الرسمية

ARTICLE_1:
المادة الأولى: تعريفات
...

ARTICLE_3:
المادة الثالثة: نسبة الضريبة
تسري الضريبة على السلع والخدمات بنسبة 14% من قيمتها...
```

### التحقق ✓:
```bash
ls data/tax_knowledge_base/
# يجب أن تظهر 3+ ملفات .txt
```

---

## الخطوة 3 — بناء RAG Service (Ingestion Pipeline)
**الهدف:** تنفيذ `backend/services/rag_service.py` — يقرأ الملفات، يقسمها chunks، يعمل embedding، ويخزن في pgvector

### الملفات:
- **تنفيذ:** `backend/services/rag_service.py` (استبدال الـ placeholder)

### الـ 4 وظائف المطلوبة:

```python
class RAGService:
    
    async def load_documents(self, docs_path: str) -> list[dict]:
        """يقرأ كل الملفات النصية من المجلد مع parse للـ metadata (law_number, article)"""
        pass

    async def chunk_documents(self, documents: list[dict]) -> list[dict]:
        """
        يقسم كل مستند لـ chunks:
        - chunk_size = 512 token
        - overlap = 50 token
        - Arabic-aware: لا يكسر في منتصف المادة
        """
        pass

    async def embed_and_store(self, chunks: list[dict], db_session) -> int:
        """يعمل embedding للـ chunks باستخدام text-embedding-3-small ويخزن في tax_chunks"""
        pass

    async def retrieve(self, query_embedding: list[float], top_k: int, threshold: float) -> list[dict]:
        """يجيب top_k chunks الأكثر صلة من pgvector بـ cosine similarity"""
        pass
```

### الـ chunking strategy المطلوبة:
- استخدم `RecursiveCharacterTextSplitter` من LangChain
- `separators = ["\nARTICLE_", "\n\n", "\n", "،", " "]` — لاحظ إن المادة separators أول
- `chunk_size = 512`, `chunk_overlap = 50`
- احتفظ بـ metadata (document_name, law_number, article) في كل chunk

### التحقق ✓:
```python
# بعد التنفيذ، اعمل:
service = RAGService()
docs = await service.load_documents("./data/tax_knowledge_base")
print(f"Loaded {len(docs)} documents")

chunks = await service.chunk_documents(docs)
print(f"Generated {len(chunks)} chunks")
# Expected: 50-200 chunks
```

---

## الخطوة 4 — سكريبت الـ Ingestion
**الهدف:** سكريبت CLI يشغل pipeline الـ ingestion مرة واحدة لملء الـ pgvector

### الملفات:
- **إنشاء:** `scripts/ingest_tax_docs.py`

### المحتوى:
```python
"""
Run once to load tax documents into pgvector.

Usage:
    python scripts/ingest_tax_docs.py
    python scripts/ingest_tax_docs.py --clear  # wipe and re-ingest
"""

import asyncio
import argparse
from backend.services.rag_service import RAGService
from backend.core.config import get_settings

async def main(clear: bool = False):
    settings = get_settings()
    service = RAGService()
    
    if clear:
        # DELETE FROM tax_chunks;
        print("Clearing existing chunks...")
        await service.clear_all()
    
    docs = await service.load_documents(settings.tax_docs_path)
    print(f"Loaded {len(docs)} documents")
    
    chunks = await service.chunk_documents(docs)
    print(f"Generated {len(chunks)} chunks")
    
    count = await service.embed_and_store(chunks, db_session=...)
    print(f"Stored {count} chunks in pgvector ✓")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(clear=args.clear))
```

### التحقق ✓:
```bash
python scripts/ingest_tax_docs.py
# Expected output:
# Loaded 3 documents
# Generated ~80 chunks
# Stored 80 chunks in pgvector ✓
```

```sql
SELECT COUNT(*) FROM tax_chunks;
-- يجب أن يرجع عدد > 0
```

---

## الخطوة 5 — Query Enhancement (HyDE + Multi-Query)
**الهدف:** بناء وظيفتين لتحسين الـ query قبل الـ retrieval

### الملفات:
- **إضافة في:** `agents/m1/tools/tax_rag_tool.py`

### وظيفة HyDE:
```python
async def _generate_hyde_embedding(query: str) -> list[float]:
    """
    HyDE: بدل ما نعمل embed للسؤال مباشرة،
    نطلب من GPT-4o-mini إجابة افتراضية ونعمل embed لها.
    ده بيخلي الـ embedding أقرب لنص القانون الفعلي.
    """
    hyde_prompt = f"""أنت مستشار ضريبي. اكتب فقرة قانونية مختصرة (2-3 جمل) 
    تجيب على هذا السؤال كما لو أنك تقتبس من نص قانوني:
    
    السؤال: {query}
    
    اكتب الإجابة مباشرة بصيغة قانونية رسمية."""
    
    response = await llm_fast.ainvoke(hyde_prompt)
    hypothetical_text = response.content
    return await embeddings.aembed_query(hypothetical_text)
```

### وظيفة Multi-Query:
```python
async def _generate_query_variations(query: str) -> list[str]:
    """
    يولد 3 صياغات مختلفة للسؤال لزيادة الـ recall.
    """
    prompt = f"""اكتب 3 صياغات مختلفة لهذا السؤال الضريبي.
    الصياغات يجب أن تكون بنفس المعنى لكن بكلمات مختلفة.
    اكتب كل صياغة في سطر منفصل، بدون ترقيم.
    
    السؤال الأصلي: {query}"""
    
    response = await llm_fast.ainvoke(prompt)
    variations = [line.strip() for line in response.content.split('\n') if line.strip()]
    return variations[:3]  # max 3 variations
```

### التحقق ✓:
```python
hyde_emb = await _generate_hyde_embedding("ما نسبة ضريبة القيمة المضافة؟")
print(f"HyDE embedding dim: {len(hyde_emb)}")  # Expected: 1536

variations = await _generate_query_variations("ما نسبة VAT؟")
print(f"Got {len(variations)} variations")  # Expected: 3
```

---

## الخطوة 6 — Retrieval + Reranking
**الهدف:** استرجاع الـ chunks الأكثر صلة وإعادة ترتيبها

### الملفات:
- **إضافة في:** `agents/m1/tools/tax_rag_tool.py`

### وظيفة الـ Retrieval:
```python
async def _retrieve_chunks(
    query: str,
    rag_service: RAGService,
    top_k: int = 5,
    threshold: float = 0.75
) -> list[dict]:
    """
    1. HyDE embedding للـ query
    2. Multi-query variations
    3. استرجاع top_k لكل query
    4. deduplicate بالـ chunk_id
    5. فلتر بالـ threshold
    """
    all_chunks = {}
    
    # HyDE retrieval
    hyde_embedding = await _generate_hyde_embedding(query)
    hyde_results = await rag_service.retrieve(hyde_embedding, top_k, threshold)
    for chunk in hyde_results:
        all_chunks[chunk["chunk_id"]] = chunk
    
    # Multi-query retrieval
    variations = await _generate_query_variations(query)
    for variation in variations:
        var_embedding = await embeddings.aembed_query(variation)
        var_results = await rag_service.retrieve(var_embedding, top_k, threshold)
        for chunk in var_results:
            if chunk["chunk_id"] not in all_chunks:
                all_chunks[chunk["chunk_id"]] = chunk
    
    return list(all_chunks.values())
```

### وظيفة الـ Reranking:
```python
async def _rerank_chunks(query: str, chunks: list[dict], top_n: int = 3) -> list[dict]:
    """
    يطلب من GPT-4o-mini تقييم كل chunk (0-10) لمدى صلته بالسؤال.
    يرجع top_n chunks بالترتيب.
    """
    if len(chunks) <= top_n:
        return chunks
    
    chunks_text = "\n---\n".join([
        f"[{i}] {c['chunk_text'][:300]}"
        for i, c in enumerate(chunks)
    ])
    
    prompt = f"""قيّم مدى صلة كل قطعة نصية بالسؤال التالي.
    أعطِ كل قطعة درجة من 0 إلى 10.
    أجب بـ JSON فقط: {{"scores": [8, 3, 9, ...]}}
    
    السؤال: {query}
    
    القطع النصية:
    {chunks_text}"""
    
    response = await llm_fast.ainvoke(prompt)
    scores = json.loads(response.content)["scores"]
    
    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in ranked[:top_n]]
```

### التحقق ✓:
```python
chunks = await _retrieve_chunks("ما نسبة VAT؟", rag_service)
print(f"Retrieved {len(chunks)} unique chunks")

reranked = await _rerank_chunks("ما نسبة VAT؟", chunks)
print(f"Top {len(reranked)} after reranking")
print(reranked[0]["article"])  # Expected: "المادة 3" or similar
```

---

## الخطوة 7 — تنفيذ `tax_rag_tool.py` (الأداة الكاملة)
**الهدف:** تنفيذ الـ tool الكامل الذي يجمع كل الخطوات السابقة

### الملفات:
- **تنفيذ:** `agents/m1/tools/tax_rag_tool.py` (استبدال الـ placeholder)

### الـ interface المطلوبة:
```python
"""
tax_rag_tool — Full Advanced RAG pipeline for tax questions.

Input:  query (str), language (str), extracted_params (dict)
Output: TaxRAGResult dict with: answer, legal_reference, confidence, disclaimer, out_of_scope
"""

from agents.shared.llm_client import llm_primary, llm_fast, embeddings
from backend.services.rag_service import RAGService
from backend.core.config import get_settings

DISCLAIMER = "توجيه استرشادي — استشر مستشاراً ضريبياً للقرارات الرسمية"

async def run_tax_rag(query: str, language: str = "ar") -> dict:
    """
    Full pipeline:
    1. Retrieve + rerank (HyDE + multi-query)
    2. Out-of-scope guard
    3. Build context from top chunks
    4. GPT-4o generation with legal citation
    5. Return structured response with mandatory disclaimer
    """
    settings = get_settings()
    rag_service = RAGService()
    
    # Step 1: Retrieve
    chunks = await _retrieve_chunks(query, rag_service, settings.rag_top_k, settings.rag_similarity_threshold)
    
    # Step 2: Out-of-scope guard
    if not chunks:
        return {
            "answer": "لا يمكنني الإجابة على هذا السؤال — خارج نطاق القواعد الضريبية المتاحة",
            "legal_reference": None,
            "confidence": 0.0,
            "sources": [],
            "disclaimer": DISCLAIMER,
            "out_of_scope": True,
        }
    
    # Step 3: Rerank
    top_chunks = await _rerank_chunks(query, chunks, top_n=3)
    
    # Step 4: Build context
    context = _build_context(top_chunks)
    
    # Step 5: Generate answer
    answer_data = await _generate_answer(query, context, language)
    
    return {
        "answer": answer_data["answer"],
        "legal_reference": answer_data["legal_reference"],
        "confidence": max(c.get("similarity", 0) for c in top_chunks),
        "sources": [c["chunk_id"] for c in top_chunks],
        "disclaimer": DISCLAIMER,
        "out_of_scope": False,
    }
```

### System prompt لـ GPT-4o:
```python
TAX_SYSTEM_PROMPT = """أنت مستشار ضريبي متخصص في القانون المصري.
أجب على الأسئلة الضريبية بناءً فقط على النصوص القانونية المقدمة.
قواعد مهمة:
1. لا تخترع معلومات غير موجودة في النصوص
2. اذكر دائماً المادة القانونية المصدر
3. الإجابة يجب أن تكون واضحة ومباشرة
4. إذا كانت المعلومات غير كافية، قل ذلك صراحةً"""
```

### التحقق ✓:
```python
result = await run_tax_rag("ما نسبة ضريبة القيمة المضافة؟")
assert result["out_of_scope"] == False
assert result["disclaimer"] == DISCLAIMER
assert result["legal_reference"] is not None
print(result["answer"])
```

---

## الخطوة 8 — إنشاء `tax_rag_node.py`
**الهدف:** إنشاء الـ LangGraph node الحقيقي الذي يستدعي الـ tool

### الملفات:
- **إنشاء:** `agents/m1/nodes/tax_rag_node.py`

### المحتوى:
```python
"""
Tax RAG Node — Sprint 4.
Replaces tax_rag_stub from Sprint 1.

Reads:  state["query"], state["language"], state["extracted_params"]
Writes: state["raw_data"], state["narrative"], state["final_response"]
"""

from agents.m1.schemas.m1_state import M1State
from agents.m1.tools.tax_rag_tool import run_tax_rag


async def tax_rag_node(state: M1State) -> dict:
    query = state.get("query", "")
    language = state.get("language", "ar")
    
    result = await run_tax_rag(query, language)
    
    return {
        "raw_data": [result],
        "data_confidence": result["confidence"],
        "narrative": result["answer"],
        "final_response": {
            "format": "narrative" if not result["out_of_scope"] else "text",
            "data": None,
            "chart_config": None,
            "narrative": result["answer"],
            "alert": None,
            "disclaimer": result["disclaimer"],
            "legal_reference": result["legal_reference"],
            "out_of_scope": result["out_of_scope"],
            "metadata": {
                "intent": "tax_reasoning",
                "confidence": result["confidence"],
                "sources": result["sources"],
                "stub": False,
            },
        },
    }
```

### التحقق ✓:
```python
state = {"query": "ما نسبة VAT؟", "language": "ar", "extracted_params": {}}
output = await tax_rag_node(state)
assert output["final_response"]["stub"] == False
assert output["final_response"]["disclaimer"] is not None
```

---

## الخطوة 9 — تحديث `m1_graph.py`
**الهدف:** استبدال `tax_rag_stub` بـ `tax_rag_node` الحقيقي

### الملفات:
- **تعديل:** `agents/m1/graphs/m1_graph.py`

### التغييرات المطلوبة (3 أسطر فقط):

```python
# حذف هذا الـ import:
from agents.m1.nodes.stub_nodes import (
    db_query_stub,
    invoice_analysis_stub,
    tax_rag_stub,           # ← احذف هذا
)

# إضافة هذا الـ import:
from agents.m1.nodes.tax_rag_node import tax_rag_node

# في build_m1_graph():
# BEFORE:
graph.add_node("tax_rag_stub", tax_rag_stub)

# AFTER:
graph.add_node("tax_rag_node", tax_rag_node)

# في add_conditional_edges:
# BEFORE:
"tax_rag_stub": "tax_rag_stub"

# AFTER:
"tax_rag_stub": "tax_rag_node"   # key يفضل نفسه لأن RouterNode يعرف "tax_rag_stub" كـ key

# في add_edge:
# BEFORE:
graph.add_edge("tax_rag_stub", "validation_enrichment")

# AFTER:
graph.add_edge("tax_rag_node", "validation_enrichment")
```

### التحقق ✓:
```python
from agents.m1.graphs.m1_graph import m1_graph
result = await m1_graph.ainvoke({
    "query": "ما نسبة ضريبة القيمة المضافة؟",
    "language": "ar"
})
assert result["final_response"]["stub"] == False
assert "ضريبة" in result["narrative"]
```

---

## الخطوة 10 — كتابة الـ Tests
**الهدف:** كتابة tests تغطي الـ scenarios المطلوبة في Sprint 4

### الملفات:
- **إنشاء:** `agents/tests/test_tax_rag.py`

### الـ tests المطلوبة:
```python
import pytest

# Test 1: In-scope Arabic question
@pytest.mark.asyncio
async def test_in_scope_arabic():
    result = await run_tax_rag("ما نسبة ضريبة القيمة المضافة؟", "ar")
    assert result["out_of_scope"] == False
    assert result["answer"] != ""
    assert result["legal_reference"] is not None
    assert result["disclaimer"] != ""

# Test 2: Out-of-scope question
@pytest.mark.asyncio
async def test_out_of_scope():
    result = await run_tax_rag("ما عاصمة فرنسا؟", "ar")
    assert result["out_of_scope"] == True

# Test 3: Disclaimer always present
@pytest.mark.asyncio
async def test_disclaimer_mandatory():
    result = await run_tax_rag("ما ضريبة الدمغة؟", "ar")
    assert "استرشادي" in result["disclaimer"]

# Test 4: English query works
@pytest.mark.asyncio
async def test_in_scope_english():
    result = await run_tax_rag("What is the VAT rate in Egypt?", "en")
    assert result["out_of_scope"] == False

# Test 5: Stub replaced in graph
def test_stub_replaced_in_graph():
    from agents.m1.graphs.m1_graph import m1_graph
    node_names = list(m1_graph.nodes.keys())
    assert "tax_rag_stub" not in node_names
    assert "tax_rag_node" in node_names

# Test 6: Full graph integration
@pytest.mark.asyncio
async def test_full_graph_tax_query():
    from agents.m1.graphs.m1_graph import m1_graph
    result = await m1_graph.ainvoke({
        "query": "ما نسبة VAT؟",
        "language": "ar",
    })
    assert result["final_response"]["stub"] == False
```

### التحقق ✓:
```bash
pytest agents/tests/test_tax_rag.py -v
# Expected: 6 passed
```

---

## ملخص الخطوات والترتيب

| # | الخطوة | الملفات | التبعية |
|---|--------|---------|---------|
| 1 | إنشاء جدول pgvector | `backend/models/tax_chunk.py` + SQL | Sprint 0 (pgvector enabled) |
| 2 | إنشاء قاعدة المعرفة | `data/tax_knowledge_base/*.txt` | لا شيء |
| 3 | بناء RAG Service | `backend/services/rag_service.py` | خطوة 1 + 2 |
| 4 | سكريبت الـ Ingestion | `scripts/ingest_tax_docs.py` | خطوة 3 |
| 5 | Query Enhancement | `agents/m1/tools/tax_rag_tool.py` (جزء) | Sprint 0 (LLM Client) |
| 6 | Retrieval + Reranking | `agents/m1/tools/tax_rag_tool.py` (جزء) | خطوة 3 + 5 |
| 7 | tax_rag_tool الكامل | `agents/m1/tools/tax_rag_tool.py` (كامل) | خطوة 5 + 6 |
| 8 | إنشاء tax_rag_node | `agents/m1/nodes/tax_rag_node.py` | خطوة 7 |
| 9 | تحديث m1_graph.py | `agents/m1/graphs/m1_graph.py` | خطوة 8 |
| 10 | الـ Tests | `agents/tests/test_tax_rag.py` | خطوة 9 |

> **ملاحظة:** خطوة 2 و خطوة 5 مستقلتان — تقدر تشتغل عليهم في نفس الوقت.
