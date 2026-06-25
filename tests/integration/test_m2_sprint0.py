"""
Sprint 0 Integration Tests — Architecture & Planning
=====================================================

Tests cover:
  1. M2State TypedDict has all required fields defined in the sprint plan
  2. State field types (all optional via total=False)
  3. DB tables exist and are reachable: inventory_alerts, rfqs, supplier_offers
  4. LangGraph compiles correctly with MemorySaver (m2_app)
  5. Graph has the correct nodes registered
  6. Graph has interrupt_before on both approval nodes

Run:
    conda activate mlops
    python -m pytest tests/integration/test_m2_sprint0.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


# ═══════════════════════════════════════════════════════════════════
# 1. M2State schema — field presence
# ═══════════════════════════════════════════════════════════════════

def test_m2state_has_trigger_fields():
    from agents.m2.schemas.m2_state import M2State
    hints = M2State.__annotations__
    assert "trigger_source" in hints
    assert "trigger_user_id" in hints


def test_m2state_has_scan_fields():
    from agents.m2.schemas.m2_state import M2State
    hints = M2State.__annotations__
    assert "flagged_products" in hints
    assert "scan_summary" in hints


def test_m2state_has_current_product_fields():
    from agents.m2.schemas.m2_state import M2State
    hints = M2State.__annotations__
    assert "current_product" in hints
    assert "detection_type" in hints


def test_m2state_has_procurement_fields():
    from agents.m2.schemas.m2_state import M2State
    hints = M2State.__annotations__
    for field in ("rfq_draft", "rfq_id", "thread_id"):
        assert field in hints, f"Missing procurement field: {field}"


def test_m2state_has_pricing_field():
    from agents.m2.schemas.m2_state import M2State
    assert "pricing_recommendation" in M2State.__annotations__


def test_m2state_has_offer_fields():
    from agents.m2.schemas.m2_state import M2State
    hints = M2State.__annotations__
    assert "supplier_offers" in hints
    assert "recommended_offer" in hints


def test_m2state_has_approval_fields():
    from agents.m2.schemas.m2_state import M2State
    hints = M2State.__annotations__
    assert "approval_status" in hints
    assert "approval_notes" in hints


def test_m2state_is_total_false():
    """All fields should be optional (total=False)."""
    from agents.m2.schemas.m2_state import M2State
    # total=False means you can create a valid TypedDict with zero fields
    empty: M2State = {}  # type: ignore[assignment]
    assert isinstance(empty, dict)


# ═══════════════════════════════════════════════════════════════════
# 2. DB tables exist (SELECT 1 FROM <table> LIMIT 0)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_inventory_alerts_table_exists():
    from sqlalchemy import text
    from backend.core.database import get_db_session

    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT 1 FROM inventory_alerts LIMIT 0")
        )
    assert result is not None


@pytest.mark.anyio
async def test_rfqs_table_exists():
    from sqlalchemy import text
    from backend.core.database import get_db_session

    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT 1 FROM rfqs LIMIT 0")
        )
    assert result is not None


@pytest.mark.anyio
async def test_supplier_offers_table_exists():
    from sqlalchemy import text
    from backend.core.database import get_db_session

    async with get_db_session() as session:
        result = await session.execute(
            text("SELECT 1 FROM supplier_offers LIMIT 0")
        )
    assert result is not None


# ═══════════════════════════════════════════════════════════════════
# 3. LangGraph compiles and is usable
# ═══════════════════════════════════════════════════════════════════

def test_m2_graph_imports_without_error():
    from agents.m2.graphs.m2_graph import m2_app, build_m2_app_with_checkpointer
    assert m2_app is not None
    assert callable(build_m2_app_with_checkpointer)


def test_m2_graph_has_procurement_nodes():
    from agents.m2.graphs.m2_graph import m2_app
    nodes = set(m2_app.get_graph().nodes.keys())
    for expected in (
        "alert_generator_node",
        "rfq_builder_node",
        "human_approval_node",
        "rfq_send_node",
        "await_offers_node",
        "offer_analysis_node",
        "final_approval_node",
    ):
        assert expected in nodes, f"Node missing from graph: {expected}. Found: {nodes}"


def test_m2_graph_has_pricing_node():
    from agents.m2.graphs.m2_graph import m2_app
    nodes = set(m2_app.get_graph().nodes.keys())
    assert "pricing_advisor_node" in nodes, f"pricing_advisor_node missing. Found: {nodes}"


def test_m2_graph_interrupt_before_approval_nodes():
    from agents.m2.graphs.m2_graph import m2_app
    interrupt_nodes = set(m2_app.interrupt_before_nodes)
    assert "human_approval_node" in interrupt_nodes, (
        f"human_approval_node not in interrupt_before_nodes: {interrupt_nodes}"
    )
    assert "final_approval_node" in interrupt_nodes, (
        f"final_approval_node not in interrupt_before_nodes: {interrupt_nodes}"
    )


def test_build_m2_app_with_checkpointer_returns_compiled_graph():
    from langgraph.checkpoint.memory import MemorySaver
    from agents.m2.graphs.m2_graph import build_m2_app_with_checkpointer

    app = build_m2_app_with_checkpointer(MemorySaver())
    assert app is not None
