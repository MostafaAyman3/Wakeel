"""
Sprint 6 Integration Tests — Human Approval + Send + Checkpointer
=================================================================

Tests cover:
  1. GET  /api/v1/m2/rfqs           — list RFQs (empty or populated)
  2. POST /api/v1/m2/rfqs/{id}/approve — approve a real pending RFQ
  3. POST /api/v1/m2/rfqs/{id}/approve — reject a real pending RFQ
  4. 404  on unknown rfq_id
  5. 409  on already-processed RFQ
  6. 422  on invalid approval_status
  7. Full flow: analyze → list RFQs → approve (end-to-end, only if low_stock data exists)

Run:
    conda activate mlops
    python -m pytest tests/integration/test_m2_sprint6.py -v
"""

import sys
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app

# ── Helpers ───────────────────────────────────────────────────────

BASE = "http://test"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


# ═══════════════════════════════════════════════════════════════════
# 1. GET /api/v1/m2/rfqs
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_list_rfqs_returns_200():
    """Endpoint always returns 200 with rfqs list and total count."""
    async with _client() as c:
        r = await c.get("/api/v1/m2/rfqs")

    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert "rfqs" in data
    assert "total" in data
    assert isinstance(data["rfqs"], list)
    assert data["total"] == len(data["rfqs"])


@pytest.mark.anyio
async def test_list_rfqs_item_schema():
    """Each RFQ item has required fields."""
    async with _client() as c:
        r = await c.get("/api/v1/m2/rfqs")

    assert r.status_code == 200
    rfqs = r.json()["rfqs"]

    for item in rfqs:
        assert "id" in item
        assert "product_id" in item
        assert "quantity" in item
        assert "unit" in item
        assert "status" in item
        assert "created_at" in item
        # status is one of the known values
        assert item["status"] in ("draft", "pending", "sent", "rejected", "cancelled")


# ═══════════════════════════════════════════════════════════════════
# 2. POST /api/v1/m2/rfqs/{id}/approve — 404 on unknown ID
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_approve_unknown_rfq_returns_404():
    """Non-existent rfq_id → 404."""
    fake_id = str(uuid.uuid4())
    async with _client() as c:
        r = await c.post(
            f"/api/v1/m2/rfqs/{fake_id}/approve",
            json={"approval_status": "approved"},
        )

    assert r.status_code == 404, r.text[:300]


# ═══════════════════════════════════════════════════════════════════
# 3. POST /api/v1/m2/rfqs/{id}/approve — 422 on bad status
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_approve_invalid_status_returns_422():
    """approval_status other than 'approved'/'rejected' → 422."""
    fake_id = str(uuid.uuid4())
    async with _client() as c:
        r = await c.post(
            f"/api/v1/m2/rfqs/{fake_id}/approve",
            json={"approval_status": "maybe"},
        )

    assert r.status_code == 422, r.text[:300]


# ═══════════════════════════════════════════════════════════════════
# 4. Full flow: create RFQ via analyze → approve it
#    Only runs when the DB has low_stock or predicted_shortage products.
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_full_approval_flow_if_rfq_exists():
    """
    End-to-end test:
      1. Call POST /analyze to generate fresh RFQs (if procurement products exist)
      2. GET /rfqs to find a draft RFQ
      3. POST /rfqs/{id}/approve  with status='approved'  → 200, sent=True
      4. GET /rfqs again → same RFQ now has status='sent'
    """
    async with _client() as c:
        # Step 1 — trigger analysis
        analyze_r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )
    assert analyze_r.status_code == 200, analyze_r.text[:300]

    async with _client() as c:
        # Step 2 — list RFQs
        list_r = await c.get("/api/v1/m2/rfqs")
    assert list_r.status_code == 200

    rfqs = list_r.json()["rfqs"]
    draft_rfqs = [r for r in rfqs if r["status"] == "draft"]

    if not draft_rfqs:
        pytest.skip(
            "No draft RFQs found — DB has no low_stock/predicted_shortage products. "
            "Run database/seeds/m2_seed_inventory.py first."
        )

    target = draft_rfqs[0]
    rfq_id = target["id"]
    thread_id = target.get("thread_id")

    assert thread_id is not None, "RFQ must have a thread_id for graph resumption"

    async with _client() as c:
        # Step 3 — approve
        approve_r = await c.post(
            f"/api/v1/m2/rfqs/{rfq_id}/approve",
            json={"approval_status": "approved", "notes": "Looks good, proceed."},
        )
    assert approve_r.status_code == 200, approve_r.text[:300]

    approve_data = approve_r.json()
    assert approve_data["approval_status"] == "approved"
    assert approve_data["sent"] is True
    assert "sent" in approve_data["message"].lower()

    async with _client() as c:
        # Step 4 — verify status changed in DB
        list_r2 = await c.get("/api/v1/m2/rfqs")
    rfqs_after = list_r2.json()["rfqs"]
    updated = next((r for r in rfqs_after if r["id"] == rfq_id), None)

    assert updated is not None
    assert updated["status"] == "sent", (
        f"Expected status='sent', got '{updated['status']}'"
    )


@pytest.mark.anyio
async def test_full_rejection_flow_if_rfq_exists():
    """
    Same as above but rejects the RFQ.
    The RFQ status should NOT become 'sent' and sent=False.
    """
    async with _client() as c:
        analyze_r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )
    assert analyze_r.status_code == 200

    async with _client() as c:
        list_r = await c.get("/api/v1/m2/rfqs")
    draft_rfqs = [r for r in list_r.json()["rfqs"] if r["status"] == "draft"]

    if not draft_rfqs:
        pytest.skip("No draft RFQs — run seed script first.")

    rfq_id = draft_rfqs[0]["id"]

    async with _client() as c:
        reject_r = await c.post(
            f"/api/v1/m2/rfqs/{rfq_id}/approve",
            json={"approval_status": "rejected", "notes": "Price too high."},
        )
    assert reject_r.status_code == 200, reject_r.text[:300]

    reject_data = reject_r.json()
    assert reject_data["approval_status"] == "rejected"
    assert reject_data["sent"] is False


# ═══════════════════════════════════════════════════════════════════
# 5. 409 on double-approve
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_double_approve_returns_409():
    """
    Approving an already-sent RFQ should return 409 Conflict.
    We first approve a draft RFQ, then try to approve it again.
    """
    async with _client() as c:
        await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )

    async with _client() as c:
        list_r = await c.get("/api/v1/m2/rfqs")
    draft_rfqs = [r for r in list_r.json()["rfqs"] if r["status"] == "draft"]

    if not draft_rfqs:
        pytest.skip("No draft RFQs — run seed script first.")

    rfq_id = draft_rfqs[0]["id"]

    # First approval
    async with _client() as c:
        r1 = await c.post(
            f"/api/v1/m2/rfqs/{rfq_id}/approve",
            json={"approval_status": "approved"},
        )
    assert r1.status_code == 200

    # Second approval on the same RFQ → 409
    async with _client() as c:
        r2 = await c.post(
            f"/api/v1/m2/rfqs/{rfq_id}/approve",
            json={"approval_status": "approved"},
        )
    assert r2.status_code == 409, r2.text[:300]
