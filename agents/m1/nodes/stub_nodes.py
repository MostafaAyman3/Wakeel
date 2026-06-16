"""
Stub Nodes — valid-state placeholder nodes for Sprint 4 tools.

Each stub returns a well-formed state dict that matches M1State,
including metadata with ``stub: true`` so downstream code and tests
can distinguish stub output from real tool output.

These will be replaced by actual implementations:
  • tax_rag_stub  → Sprint 4 (Tax RAG)

Sprint 3 Note:
  invoice_analysis_stub has been REMOVED — replaced by the real
  InvoiceAnalysisToolNode in agents/m1/nodes/invoice_analysis_tool_node.py
"""

from __future__ import annotations

from agents.m1.schemas.m1_state import M1State


def _build_stub_response(state: M1State, pending_sprint: int) -> dict:
    """Shared helper — builds a valid final_response with stub metadata."""
    return {
        "raw_data": [],
        "final_response": {
            "format": "direct_text",
            "data": None,
            "chart_config": None,
            "narrative": None,
            "alert": None,
            "disclaimer": None,
            "metadata": {
                "intent": state.get("intent", ""),
                "extracted_params": state.get("extracted_params", {}),
                "confidence": state.get("intent_confidence", 0.0),
                "stub": True,
                "pending_sprint": pending_sprint,
            },
        },
    }


async def tax_rag_stub(state: M1State) -> dict:
    """Placeholder for Sprint 4 — Tax RAG (pgvector retrieval)."""
    return _build_stub_response(state, pending_sprint=4)
