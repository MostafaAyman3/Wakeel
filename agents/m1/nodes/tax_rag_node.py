
"""
Tax RAG Node — Sprint 4 LangGraph Node.

Replaces: agents/m1/nodes/stub_nodes.py :: tax_rag_stub

Position in graph:
    RouterNode → tax_rag_node → ValidationEnrichmentNode → END

Reads from M1State:
    state["query"]             — user's tax question (AR or EN)
    state["language"]          — "ar" | "en"
    state["extracted_params"]  — any pre-extracted parameters from classifier

Writes to M1State:
    state["raw_data"]          — list containing the TaxRAGResult dict
    state["data_confidence"]   — confidence score of best retrieved chunk [0,1]
    state["narrative"]         — the LLM-generated answer text
    state["output_format"]     — always "narrative" for tax RAG responses
    state["final_response"]    — complete structured response payload

Delegates all RAG logic to:
    agents/m1/tools/tax_rag_tool.py :: run_tax_rag()

This node is ONLY responsible for:
    1. Reading from state
    2. Calling run_tax_rag()
    3. Writing results back to state in M1State format
"""

from __future__ import annotations

import logging

from agents.m1.schemas.m1_state import M1State
from agents.m1.tools.tax_rag_tool import DISCLAIMER, run_tax_rag

logger = logging.getLogger(__name__)

# Fallback error messages (node-level, not RAG-level)
_ERROR_AR = "حدث خطأ غير متوقع أثناء معالجة سؤالك الضريبي. يُرجى المحاولة مرة أخرى."
_ERROR_EN = "An unexpected error occurred while processing your tax question. Please try again."


async def tax_rag_node(state: M1State) -> dict:
    """
    LangGraph node: execute full Tax RAG pipeline and update state.

    Args:
        state: Current M1State (must contain "query" and "language").

    Returns:
        Partial M1State dict with updated fields:
        {
            "raw_data":         [TaxRAGResult dict],
            "data_confidence":  float,
            "narrative":        str,
            "output_format":    "narrative",
            "final_response":   dict,
        }
    """
    query    = state.get("query", "").strip()
    language = state.get("language", "ar")

    logger.info("tax_rag_node: query='%s…' language=%s", query[:60], language)

    if not query:
        logger.warning("tax_rag_node: empty query in state")
        return _error_state(language, "empty query")

    # ── Delegate to tool ──────────────────────────────────────────────────
    try:
        rag_result = await run_tax_rag(query=query, language=language)
    except Exception as exc:
        logger.error("tax_rag_node: run_tax_rag raised unexpectedly: %s", exc)
        return _error_state(language, str(exc))

    # ── Map RAG result → M1State fields ───────────────────────────────────
    answer     = rag_result["answer"]
    confidence = rag_result["confidence"]

    final_response = {
        "type":            "tax_rag",
        "answer":          answer,
        "legal_reference": rag_result["legal_reference"],
        "confidence":      confidence,
        "sources":         rag_result["sources"],
        "disclaimer":      rag_result["disclaimer"],
        "out_of_scope":    rag_result["out_of_scope"],
    }

    logger.info(
        "tax_rag_node: done | out_of_scope=%s | confidence=%.3f",
        rag_result["out_of_scope"], confidence,
    )

    return {
        "raw_data":        [rag_result],
        "data_confidence": confidence,
        "narrative":       answer,
        "output_format":   "narrative",
        "final_response":  final_response,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _error_state(language: str, reason: str) -> dict:
    """Return a safe error state that keeps the graph moving without crashing."""
    message = _ERROR_AR if language == "ar" else _ERROR_EN

    final_response = {
        "type":            "tax_rag",
        "answer":          message,
        "legal_reference": None,
        "confidence":      0.0,
        "sources":         [],
        "disclaimer":      DISCLAIMER,
        "out_of_scope":    True,
        "error":           reason,
    }

    return {
        "raw_data":        [],
        "data_confidence": 0.0,
        "narrative":       message,
        "output_format":   "narrative",
        "final_response":  final_response,
        "error":           reason,
    }
