import pytest
import sys
from pathlib import Path

# Add the project root to sys.path so 'backend' can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from httpx import AsyncClient, ASGITransport
from backend.main import app


# ── Tests ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_m2_inventory_endpoint():
    """
    GET /api/v1/m2/inventory should return 200 with products, summary, alerts.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/m2/inventory")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}. Body: {response.text[:300]}"
    )
    data = response.json()
    assert "products" in data, "Response missing 'products' key"
    assert "summary" in data, "Response missing 'summary' key"
    assert isinstance(data["products"], list)


@pytest.mark.anyio
async def test_m2_analyze_endpoint():
    """
    POST /api/v1/m2/analyze should return 200 with scan_summary, alerts, rfq_drafts.
    """
    payload = {"trigger_source": "manual", "language": "en"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/m2/analyze", json=payload)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}. Body: {response.text[:300]}"
    )
    data = response.json()
    assert "scan_summary" in data
    assert "alerts" in data
    assert "rfq_drafts" in data
    assert "language" in data
    assert data["language"] == "en"
