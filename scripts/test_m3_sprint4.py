"""
M3 Sprint 4 Integration Tests — Human Review Gate + Escalation + Audit Trail.

Tests all Sprint 4 components:

  Pure functions (no I/O):
    1. _contains_financial_commitment() — EN & AR keywords
    2. _get_escalation_reason() — no-data vs missing-fields vs fallback
    3. _review_router() — escalation vs end
    4. _escalation_router() — unchanged regression check

  Async nodes (audit call wrapped in try/except — no DB required):
    5. human_review_gate() — all 6 routing rules
    6. escalate_case() — EN + AR output, summary structure, graceful audit failure

  Graph:
    7. build_support_graph() compiles with 9 expected nodes
    8. Conditional edge labels match router outputs

  Schema:
    9. build_initial_state() includes escalation_summary

  Services (with mocked audit trail):
    10. approve_response() — returns correct dict
    11. reject_response() — returns rejection_context
    12. escalate_manually() — returns escalation_reason

  API schemas:
    13. SupportRequest accepts rejection_context
    14. SupportResponse includes final_response + escalation_summary

Usage:
    python scripts/test_m3_sprint4.py
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force UTF-8 on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── Test environment (no DB / LLM required) ──────────────────────────────
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("READONLY_DB_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_HOURS", "24")
os.environ.setdefault("APP_NAME", "WakeelTest")

# Configure structlog before any project imports
from backend.core.logging import configure_logging
configure_logging()

PASS = "PASS"
FAIL = "FAIL"
results: list[tuple[str, str]] = []


def log(tc_id: str, name: str, passed: bool, note: str = "") -> None:
    status = PASS if passed else FAIL
    results.append((tc_id, status))
    suffix = f" — {note}" if note else ""
    marker = "[OK]" if passed else "[!!]"
    print(f"  {marker}  [{tc_id}] {name}{suffix}")


# ══════════════════════════════════════════════════════════════════════════
#  1. Financial commitment detection
# ══════════════════════════════════════════════════════════════════════════

def test_contains_financial_commitment():
    from agents.m3.nodes.human_review_node import _contains_financial_commitment

    # EN financial keywords
    assert _contains_financial_commitment("We will refund your money")
    assert _contains_financial_commitment("You will receive compensation")
    assert _contains_financial_commitment("A discount of 10%")
    assert _contains_financial_commitment("We will pay the amount")
    assert _contains_financial_commitment("You will receive a credit")
    assert _contains_financial_commitment("We will reimburse you")
    assert _contains_financial_commitment("We will waive the fee")

    # AR financial keywords
    assert _contains_financial_commitment("سيتم استرداد المبلغ")
    assert _contains_financial_commitment("سوف تحصل على تعويض")
    assert _contains_financial_commitment("تم تطبيق خصم")
    assert _contains_financial_commitment("سيدفع العميل")

    # EN delivery promise keywords
    assert _contains_financial_commitment("Your order will arrive tomorrow")
    assert _contains_financial_commitment("It will be delivered by Friday")
    assert _contains_financial_commitment("It will arrive within 3 days")

    # AR delivery promise keywords
    assert _contains_financial_commitment("سيصل الطلب قريباً")
    assert _contains_financial_commitment("سيتم التوصيل غداً")
    assert _contains_financial_commitment("خلال 3 أيام")

    # Should NOT match safe responses
    assert not _contains_financial_commitment("")
    assert not _contains_financial_commitment("Your order status is confirmed")
    assert not _contains_financial_commitment("We have received your request")
    assert not _contains_financial_commitment(None)

    log("TC-01", "Financial/delivery commitment detection", True)


# ══════════════════════════════════════════════════════════════════════════
#  2. Escalation reason detection
# ══════════════════════════════════════════════════════════════════════════

def test_get_escalation_reason():
    from agents.m3.nodes.escalation_node import _get_escalation_reason

    # No data
    r1 = _get_escalation_reason({"data_completeness": 0.0, "missing_fields": []})
    assert "No data found" in r1

    # Missing fields
    r2 = _get_escalation_reason({"data_completeness": 0.5, "missing_fields": ["shipping", "history"]})
    assert "Missing data sources" in r2
    assert "shipping" in r2

    # Fallback
    r3 = _get_escalation_reason({"data_completeness": 1.0, "missing_fields": []})
    assert r3 == "System escalation flag set"

    log("TC-02", "Escalation reason detection", True)


# ══════════════════════════════════════════════════════════════════════════
#  3. Graph routers
# ══════════════════════════════════════════════════════════════════════════

def test_graph_routers():
    from agents.m3.graphs.m3_graph import _escalation_router, _review_router

    # _escalation_router — unchanged from Sprint 3
    assert _escalation_router({"escalation_needed": True}) == "escalate"
    assert _escalation_router({"escalation_needed": False}) == "classify"
    assert _escalation_router({}) == "classify"

    # _review_router — Sprint 4
    assert _review_router({"escalation_needed": True}) == "escalate"
    assert _review_router({"escalation_needed": False}) == "end"
    assert _review_router({}) == "end"

    log("TC-03", "Graph conditional routers", True)


# ══════════════════════════════════════════════════════════════════════════
#  4. HumanReviewGateNode — all 6 routing rules
# ══════════════════════════════════════════════════════════════════════════

async def test_human_review_gate():
    from agents.m3.nodes.human_review_node import human_review_gate

    # Rule 1: escalation_needed → skip review
    r = await human_review_gate({
        "escalation_needed": True,
        "issue_type": "billing_dispute",
        "confidence_score": 0.9,
        "draft_response": "ok",
    })
    assert r == {"review_required": False}, f"Expected no review for escalation, got {r}"

    # Rule 2: billing_dispute → mandatory review
    r = await human_review_gate({
        "escalation_needed": False,
        "issue_type": "billing_dispute",
        "confidence_score": 0.95,
        "draft_response": "",
    })
    assert r == {"review_required": True}, f"Expected review for billing_dispute, got {r}"

    # Rule 3: refund_request → mandatory review
    r = await human_review_gate({
        "escalation_needed": False,
        "issue_type": "refund_request",
        "confidence_score": 0.95,
        "draft_response": "",
    })
    assert r == {"review_required": True}, f"Expected review for refund_request, got {r}"

    # Rule 4: confidence < 0.70 → mandatory review
    r = await human_review_gate({
        "escalation_needed": False,
        "issue_type": "status_inquiry",
        "confidence_score": 0.45,
        "draft_response": "",
    })
    assert r == {"review_required": True}, f"Expected review for low confidence, got {r}"

    # Rule 5: financial commitment in draft → mandatory review
    r = await human_review_gate({
        "escalation_needed": False,
        "issue_type": "status_inquiry",
        "confidence_score": 0.95,
        "draft_response": "We will refund your money",
    })
    assert r == {"review_required": True}, f"Expected review for financial commitment, got {r}"

    # Rule 6: status_inquiry + high confidence → no review
    r = await human_review_gate({
        "escalation_needed": False,
        "issue_type": "status_inquiry",
        "confidence_score": 0.95,
        "draft_response": "Your order is on its way",
    })
    assert r == {"review_required": False}, f"Expected no review for safe case, got {r}"

    # Rule 6b: general_complaint + high confidence → no review
    r = await human_review_gate({
        "escalation_needed": False,
        "issue_type": "general_complaint",
        "confidence_score": 0.85,
        "draft_response": "We appreciate your feedback",
    })
    assert r == {"review_required": False}, f"Expected no review for general_complaint, got {r}"

    log("TC-04", "HumanReviewGateNode — all 6 routing rules", True)


# ══════════════════════════════════════════════════════════════════════════
#  5. EscalationNode — output structure & graceful audit failure
# ══════════════════════════════════════════════════════════════════════════

async def test_escalation_node():
    from agents.m3.nodes.escalation_node import escalate_case

    # EN escalation
    r = await escalate_case({
        "customer_identifier": {"type": "order_id", "value": "ORD-123"},
        "issue_type": "shipping_issue",
        "fetched_data": {"invoice": {}, "order": {}, "shipping": None, "history": None},
        "issue_description": "Where is my order?",
        "data_completeness": 0.5,
        "missing_fields": ["shipping", "history"],
        "confidence_score": 0.3,
        "language": "en",
    })
    assert "final_response" in r
    assert "escalation_summary" in r
    assert "support representative" in r["final_response"].lower()
    assert r["escalation_summary"]["identifier"] == {"type": "order_id", "value": "ORD-123"}
    assert r["escalation_summary"]["issue_type"] == "shipping_issue"
    assert "Missing data sources" in r["escalation_summary"]["escalation_reason"]

    # AR escalation
    r_ar = await escalate_case({
        "customer_identifier": {"type": "invoice_id", "value": "INV-001"},
        "issue_type": "billing_dispute",
        "fetched_data": {},
        "issue_description": "فاتورة خطأ",
        "data_completeness": 0.0,
        "missing_fields": ["invoice", "order", "shipping", "history"],
        "confidence_score": 0.0,
        "language": "ar",
    })
    assert "فريق الدعم" in r_ar["final_response"]
    assert r_ar["escalation_summary"]["escalation_reason"].startswith("No data found")

    # Graceful audit failure (no DB) — should not crash
    assert "error" not in r
    assert "error" not in r_ar

    log("TC-05", "EscalationNode — EN/AR output, summary, graceful audit failure", True)


# ══════════════════════════════════════════════════════════════════════════
#  6. Graph compilation — nodes present
# ══════════════════════════════════════════════════════════════════════════

def test_graph_compilation():
    from agents.m3.graphs.m3_graph import build_support_graph

    graph = build_support_graph()
    node_names = list(graph.nodes.keys())

    # Required nodes must all be present. Extra nodes (intent_router, greeting,
    # rag, clarification_node, …) are allowed as the graph grows.
    required = {
        "intent_router", "greeting_node", "rag_node",
        "input_parser", "data_fetcher", "completeness_check",
        "issue_classifier", "context_builder", "response_generator",
        "human_review_gate", "escalation_node", "clarification_node",
    }
    missing = required - set(node_names)
    assert not missing, f"Missing nodes: {missing}"

    log("TC-06", "Graph compilation — all required nodes present", True)


# ══════════════════════════════════════════════════════════════════════════
#  7. Schema — build_initial_state includes escalation_summary
# ══════════════════════════════════════════════════════════════════════════

def test_initial_state_schema():
    from agents.m3.schemas.m3_state import build_initial_state

    state = build_initial_state(query="test query")
    assert "escalation_summary" in state
    assert state["escalation_summary"] == {}
    assert "review_required" in state
    assert state["review_required"] is False
    assert "final_response" in state
    assert state["final_response"] == ""

    # With identifier
    state2 = build_initial_state(query="test", identifier={"type": "order_id", "value": "ORD-1"})
    assert state2["customer_identifier"] == {"type": "order_id", "value": "ORD-1"}

    log("TC-07", "build_initial_state — escalation_summary field present", True)


# ══════════════════════════════════════════════════════════════════════════
#  8. Graph conditional edge labels match router outputs
# ══════════════════════════════════════════════════════════════════════════

def test_graph_conditional_labels():
    from langgraph.graph import END, START, StateGraph
    from agents.m3.schemas.m3_state import M3State
    from agents.m3.graphs.m3_graph import _review_router, _escalation_router

    # Build a minimal graph to verify edge labels exist
    graph = StateGraph(M3State)
    graph.add_node("human_review_gate", lambda s: s)
    graph.add_node("escalation_node", lambda s: s)

    graph.add_conditional_edges(
        "human_review_gate",
        _review_router,
        {"escalate": "escalation_node", "end": END},
    )

    # Verify router return values match edge labels
    router_return_escalate = _review_router({"escalation_needed": True})
    router_return_end = _review_router({"escalation_needed": False})
    assert router_return_escalate == "escalate"
    assert router_return_end == "end"

    log("TC-08", "Graph conditional edge labels match router outputs", True)


# ══════════════════════════════════════════════════════════════════════════
#  9. Services — approve/reject/escalate with mocked audit
# ══════════════════════════════════════════════════════════════════════════

async def test_approve_response():
    from backend.services.human_review_service import approve_response

    with patch("backend.services.human_review_service.log_decision", new_callable=AsyncMock) as mock_log:
        result = await approve_response(
            case_id="ORD-123",
            draft_response="Your order is confirmed",
            issue_type="status_inquiry",
            confidence_score=0.95,
            reviewed_by="user-1",
        )
        assert result["case_id"] == "ORD-123"
        assert result["action"] == "approved"
        assert result["final_response"] == "Your order is confirmed"
        mock_log.assert_awaited_once()

    log("TC-09", "approve_response — correct return structure", True)


async def test_reject_response():
    from backend.services.human_review_service import reject_response

    with patch("backend.services.human_review_service.log_decision", new_callable=AsyncMock) as mock_log:
        result = await reject_response(
            case_id="ORD-123",
            draft_response="Your order is confirmed",
            feedback="This response is inaccurate",
            issue_type="billing_dispute",
            confidence_score=0.4,
            reviewed_by="user-1",
        )
        assert result["case_id"] == "ORD-123"
        assert result["action"] == "rejected"
        assert result["rejection_context"]["reason"] == "human_rejection"
        assert result["rejection_context"]["feedback"] == "This response is inaccurate"
        assert result["rejection_context"]["previous_draft"] == "Your order is confirmed"
        mock_log.assert_awaited_once()

    log("TC-10", "reject_response — rejection_context structure", True)


async def test_escalate_manually():
    from backend.services.human_review_service import escalate_manually

    with patch("backend.services.human_review_service.log_decision", new_callable=AsyncMock) as mock_log:
        result = await escalate_manually(
            case_id="ORD-123",
            issue_type="billing_dispute",
            confidence_score=0.3,
            reviewed_by="user-1",
            reason="Customer is requesting manager",
        )
        assert result["case_id"] == "ORD-123"
        assert result["action"] == "escalated"
        assert result["escalation_reason"] == "Customer is requesting manager"
        mock_log.assert_awaited_once()

    # Default reason when not provided
    with patch("backend.services.human_review_service.log_decision", new_callable=AsyncMock):
        result2 = await escalate_manually(case_id="ORD-456")
        assert result2["escalation_reason"] == "Manual escalation by reviewer"

    log("TC-11", "escalate_manually — correct return structure", True)


# ══════════════════════════════════════════════════════════════════════════
#  10. API schemas — new fields
# ══════════════════════════════════════════════════════════════════════════

def test_api_schemas():
    from backend.api.v1.m3_support import SupportRequest, SupportResponse

    # SupportRequest accepts rejection_context
    req = SupportRequest(query="test", rejection_context={"reason": "human_rejection", "feedback": "bad"})
    assert req.query == "test"
    assert req.rejection_context == {"reason": "human_rejection", "feedback": "bad"}

    # SupportRequest without rejection_context (backwards compat)
    req2 = SupportRequest(query="test")
    assert req2.rejection_context is None

    # SupportResponse includes new Sprint 4 fields
    resp = SupportResponse(
        draft_response="draft",
        final_response="final",
        confidence_score=0.0,
        confidence_label="Low",
        review_required=True,
        escalation_needed=False,
        escalation_summary={"key": "val"},
        issue_type="status_inquiry",
        transparency_data={},
        missing_fields=[],
    )
    assert resp.final_response == "final"
    assert resp.escalation_summary == {"key": "val"}

    log("TC-12", "API schemas — Sprint 4 fields present", True)


# ══════════════════════════════════════════════════════════════════════════
#  Runner
# ══════════════════════════════════════════════════════════════════════════

async def main():
    print("\n" + "=" * 70)
    print("  M3 Sprint 4 — Human Review Gate + Escalation Tests")
    print("=" * 70 + "\n")

    # Pure functions
    test_contains_financial_commitment()
    test_get_escalation_reason()
    test_graph_routers()

    # Async nodes
    await test_human_review_gate()
    await test_escalation_node()

    # Graph
    test_graph_compilation()
    test_graph_conditional_labels()

    # Schema
    test_initial_state_schema()

    # Services (mocked audit)
    await test_approve_response()
    await test_reject_response()
    await test_escalate_manually()

    # API schemas
    test_api_schemas()

    print("\n" + "=" * 70)
    passed_count = sum(1 for _, s in results if s == PASS)
    failed_count = len(results) - passed_count
    print(f"  Results: {passed_count}/{len(results)} PASSED  |  {failed_count} FAILED")
    print("=" * 70 + "\n")

    if failed_count > 0:
        print("Failed cases:")
        for tc_id, status in results:
            if status != PASS:
                print(f"  {status}  {tc_id}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
