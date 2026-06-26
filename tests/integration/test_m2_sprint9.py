"""
Sprint 9 Integration Tests — n8n Automation & Webhooks
======================================================

Sprint 9 implemented:
  - Workflow 1: Daily cron → POST /analyze → format → Gmail
  - Workflow 2: RFQ approved → webhook → n8n → Email to vendor
  - vendor_email + vendor_name stored on rfqs table
  - _fire_webhook() real httpx POST in rfq_send_node.py
  - N8N_RFQ_WEBHOOK_URL in .env + Settings

Tests cover:
  1. Settings has n8n_rfq_webhook_url field
  2. _fire_webhook skips gracefully when URL is empty (no error)
  3. RFQ ORM model has vendor_email + vendor_name columns
  4. rfqs DB table has vendor_email + vendor_name columns
  5. webhook payload structure contains all required vendor fields
  6. Migration 006 file exists (vendor_email alter)
  7. n8n workflow JSON files exist

Run:
    conda activate mlops
    python -m pytest tests/integration/test_m2_sprint9.py -v
"""

import sys
import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app

BASE = "http://test"


# ═══════════════════════════════════════════════════════════════════
# 1. Settings — n8n webhook URL
# ═══════════════════════════════════════════════════════════════════

def test_settings_has_n8n_rfq_webhook_url():
    from backend.core.config import get_settings
    settings = get_settings()
    assert hasattr(settings, "n8n_rfq_webhook_url"), (
        "Settings missing n8n_rfq_webhook_url — add it to config.py"
    )


def test_settings_n8n_rfq_webhook_url_is_string():
    from backend.core.config import get_settings
    settings = get_settings()
    assert isinstance(settings.n8n_rfq_webhook_url, str)


# ═══════════════════════════════════════════════════════════════════
# 2. _fire_webhook graceful skip when URL is empty
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_fire_webhook_skips_without_error_when_url_empty(monkeypatch):
    """
    When n8n_rfq_webhook_url is empty, _fire_webhook should return
    immediately without raising or making any HTTP call.
    """
    from backend.core.config import get_settings, Settings
    from unittest.mock import patch, AsyncMock

    with patch.object(get_settings(), "n8n_rfq_webhook_url", ""):
        with patch("backend.core.config.get_settings") as mock_settings_fn:
            mock_s = mock_settings_fn.return_value
            mock_s.n8n_rfq_webhook_url = ""

            from agents.m2.nodes.rfq_send_node import _fire_webhook

            # Should not raise
            await _fire_webhook({"event": "rfq_sent", "rfq_id": "test-123"})


@pytest.mark.anyio
async def test_fire_webhook_does_not_raise_on_connection_error():
    """
    When URL is set but server is unreachable, _fire_webhook should
    log a warning but NOT raise (keeps the main graph flow alive).
    """
    from unittest.mock import patch, MagicMock

    with patch("backend.core.config.get_settings") as mock_fn:
        mock_fn.return_value.n8n_rfq_webhook_url = "http://127.0.0.1:19999/no-server"

        from agents.m2.nodes.rfq_send_node import _fire_webhook

        # Should not raise even on connection error
        try:
            await _fire_webhook({"event": "rfq_sent", "rfq_id": "test-456"})
        except Exception as e:
            pytest.fail(f"_fire_webhook raised an exception: {e}")


# ═══════════════════════════════════════════════════════════════════
# 3. RFQ ORM model — vendor fields
# ═══════════════════════════════════════════════════════════════════

def test_rfq_model_has_vendor_email_field():
    from backend.models.m2_rfq import RFQ
    assert hasattr(RFQ, "vendor_email"), (
        "RFQ model missing vendor_email — run migration 006"
    )


def test_rfq_model_has_vendor_name_field():
    from backend.models.m2_rfq import RFQ
    assert hasattr(RFQ, "vendor_name"), (
        "RFQ model missing vendor_name — run migration 006"
    )


# ═══════════════════════════════════════════════════════════════════
# 4. rfqs DB table — vendor_email + vendor_name columns exist
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_rfqs_table_has_vendor_email_column():
    from sqlalchemy import text
    from backend.core.database import get_db_session

    async with get_db_session() as session:
        result = await session.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'rfqs' AND column_name = 'vendor_email'
        """))
        row = result.fetchone()

    assert row is not None, (
        "rfqs.vendor_email column not found — run: "
        "ALTER TABLE rfqs ADD COLUMN IF NOT EXISTS vendor_email VARCHAR(200);"
    )


@pytest.mark.anyio
async def test_rfqs_table_has_vendor_name_column():
    from sqlalchemy import text
    from backend.core.database import get_db_session

    async with get_db_session() as session:
        result = await session.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'rfqs' AND column_name = 'vendor_name'
        """))
        row = result.fetchone()

    assert row is not None, (
        "rfqs.vendor_name column not found — run: "
        "ALTER TABLE rfqs ADD COLUMN IF NOT EXISTS vendor_name VARCHAR(200);"
    )


# ═══════════════════════════════════════════════════════════════════
# 5. Webhook payload structure
# ═══════════════════════════════════════════════════════════════════

def test_rfq_send_node_imports_without_error():
    from agents.m2.nodes.rfq_send_node import rfq_send_node, _fire_webhook
    assert callable(rfq_send_node)
    assert callable(_fire_webhook)


def test_rfq_send_node_fire_webhook_is_async():
    """_fire_webhook must be async (uses httpx.AsyncClient)."""
    import inspect
    from agents.m2.nodes.rfq_send_node import _fire_webhook
    assert inspect.iscoroutinefunction(_fire_webhook), (
        "_fire_webhook must be an async function"
    )


def test_webhook_payload_required_fields_documented():
    """
    The webhook payload sent to n8n must include vendor_email and vendor_name.
    We verify this by reading rfq_send_node source.
    """
    node_file = Path(__file__).resolve().parents[2] / "agents/m2/nodes/rfq_send_node.py"
    content = node_file.read_text(encoding="utf-8")
    assert '"vendor_email"' in content or "'vendor_email'" in content, (
        "rfq_send_node.py does not include vendor_email in webhook payload"
    )
    assert '"vendor_name"' in content or "'vendor_name'" in content, (
        "rfq_send_node.py does not include vendor_name in webhook payload"
    )


# ═══════════════════════════════════════════════════════════════════
# 6. Migration file exists
# ═══════════════════════════════════════════════════════════════════

def test_migration_006_vendor_fields_exists():
    migration = (
        Path(__file__).resolve().parents[2]
        / "database/migrations/m2/006_alter_rfqs_add_vendor_fields.sql"
    )
    assert migration.exists(), (
        "Migration 006 not found: database/migrations/m2/006_alter_rfqs_add_vendor_fields.sql"
    )


def test_migration_006_contains_vendor_email_alter():
    migration = (
        Path(__file__).resolve().parents[2]
        / "database/migrations/m2/006_alter_rfqs_add_vendor_fields.sql"
    )
    content = migration.read_text(encoding="utf-8")
    assert "vendor_email" in content.lower(), (
        "Migration 006 does not contain vendor_email column"
    )


# ═══════════════════════════════════════════════════════════════════
# 7. n8n workflow JSON files exist
# ═══════════════════════════════════════════════════════════════════

def test_n8n_workflow1_daily_analysis_exists():
    wf = (
        Path(__file__).resolve().parents[2]
        / "n8n/workflows/m2_workflow1_daily_analysis.json"
    )
    assert wf.exists(), (
        "n8n/workflows/m2_workflow1_daily_analysis.json not found"
    )


def test_n8n_workflow2_send_rfq_exists():
    wf = (
        Path(__file__).resolve().parents[2]
        / "n8n/workflows/m2_workflow2_send_rfq.json"
    )
    assert wf.exists(), (
        "n8n/workflows/m2_workflow2_send_rfq.json not found"
    )


# ═══════════════════════════════════════════════════════════════════
# 8. M2 State has vendor fields
# ═══════════════════════════════════════════════════════════════════

def test_m2_state_has_vendor_email():
    from agents.m2.schemas.m2_state import M2State
    annotations = M2State.__annotations__
    assert "vendor_email" in annotations, (
        "M2State missing vendor_email field"
    )


def test_m2_state_has_vendor_name():
    from agents.m2.schemas.m2_state import M2State
    annotations = M2State.__annotations__
    assert "vendor_name" in annotations, (
        "M2State missing vendor_name field"
    )
