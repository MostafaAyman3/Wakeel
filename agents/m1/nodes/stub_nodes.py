"""
Stub Nodes — valid-state placeholder nodes for Sprint 2 / 3 / 4 tools.

Each stub returns a well-formed state dict that matches M1State,
including metadata with ``stub: true`` so downstream code and tests
can distinguish stub output from real tool output.

These will be replaced by actual implementations:
  • db_query_stub         → Sprint 2 (Dynamic Query Builder)
  • invoice_analysis_stub → Sprint 3 (Invoice Analysis Tool)
  • tax_rag_stub          → Sprint 4 (Tax RAG)
"""

from __future__ import annotations

from agents.m1.schemas.m1_state import M1State


def _build_stub_response(state: M1State, pending_sprint: int) -> dict:
    """Shared helper — builds a valid final_response with stub metadata."""
    return {
        "raw_data": [],
        "final_response": {
            "format": "text",
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



async def invoice_analysis_stub(state: M1State) -> dict:
    """Placeholder for Sprint 3 — Invoice Analysis Tool (4-node sub-pipeline)."""
    return _build_stub_response(state, pending_sprint=3)


async def tax_rag_stub(state: M1State) -> dict:
    """Placeholder for Sprint 4 — Tax RAG (pgvector retrieval)."""
    return _build_stub_response(state, pending_sprint=4)
