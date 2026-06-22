import pytest
import sys
import os
from pathlib import Path

# Add the project root to sys.path so 'backend' can be imported
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_m2_inventory_endpoint():
    """
    Test the GET /api/v1/m2/inventory endpoint.
    It should return a 200 OK and include 'products', 'summary', and 'alerts'.
    """
    response = client.get("/api/v1/m2/inventory")
    assert response.status_code == 200
    data = response.json()
    assert "products" in data
    assert "summary" in data
    assert "alerts" in data
    
def test_m2_analyze_endpoint():
    """
    Test the POST /api/v1/m2/analyze endpoint.
    It triggers the M2 LangGraph pipeline and returns alerts, RFQs, etc.
    """
    payload = {
        "trigger_source": "manual",
        "language": "en"
    }
    response = client.post("/api/v1/m2/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "scan_summary" in data
    assert "alerts" in data
    assert "rfq_drafts" in data
    assert "language" in data
    assert data["language"] == "en"

if __name__ == "__main__":
    pytest.main(["-v", __file__])

