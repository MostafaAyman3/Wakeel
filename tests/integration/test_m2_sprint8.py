"""
Sprint 8 Integration Tests — Speech-to-Speech (Voice Assistant)
===============================================================

Sprint 8 built:
  - POST /api/v1/m2/voice endpoint
  - speech_service (STT via OpenAI Whisper + TTS via ElevenLabs)
  - VoiceAssistantPanel.tsx frontend component

Tests cover:
  1. Endpoint is registered (POST /voice exists)
  2. Missing audio file → 422
  3. speech_service module imports without error
  4. ElevenLabs API key is configured in Settings
  5. speech_to_text and text_to_speech methods exist
  6. VoiceAssistantPanel.tsx component file exists and is non-empty
  7. Voice endpoint returns audio/mpeg media type (mocked audio)

Run:
    conda activate mlops
    python -m pytest tests/integration/test_m2_sprint8.py -v
"""

import io
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app

BASE = "http://test"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


# ═══════════════════════════════════════════════════════════════════
# 1. Endpoint registration
# ═══════════════════════════════════════════════════════════════════

def test_voice_router_imports_without_error():
    from backend.api.v1.m2_voice import router
    assert router is not None


@pytest.mark.anyio
async def test_voice_endpoint_exists_not_404():
    """
    POST /voice without a file should return 422 (Unprocessable Entity),
    NOT 404 (Not Found). 422 proves the endpoint is registered.
    """
    async with _client() as c:
        r = await c.post("/api/v1/m2/voice")
    assert r.status_code != 404, (
        "POST /api/v1/m2/voice returned 404 — route is not registered in main.py"
    )


# ═══════════════════════════════════════════════════════════════════
# 2. Validation: missing audio → 422
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_voice_missing_audio_returns_422():
    """Audio is a required File field — omitting it returns 422."""
    async with _client() as c:
        r = await c.post("/api/v1/m2/voice", data={"language": "ar-EG"})
    assert r.status_code == 422, r.text[:300]


# ═══════════════════════════════════════════════════════════════════
# 3. speech_service module
# ═══════════════════════════════════════════════════════════════════

def test_speech_service_module_imports():
    from backend.services.speech_service import speech_service
    assert speech_service is not None


def test_speech_service_has_stt_method():
    from backend.services.speech_service import speech_service
    assert hasattr(speech_service, "speech_to_text"), (
        "speech_service missing speech_to_text method"
    )
    assert callable(speech_service.speech_to_text)


def test_speech_service_has_tts_method():
    from backend.services.speech_service import speech_service
    assert hasattr(speech_service, "text_to_speech"), (
        "speech_service missing text_to_speech method"
    )
    assert callable(speech_service.text_to_speech)


# ═══════════════════════════════════════════════════════════════════
# 4. Settings — ElevenLabs key exists
# ═══════════════════════════════════════════════════════════════════

def test_settings_has_elevenlabs_api_key():
    from backend.core.config import get_settings
    settings = get_settings()
    assert hasattr(settings, "elevenlabs_api_key"), (
        "Settings missing elevenlabs_api_key field"
    )


def test_settings_elevenlabs_key_is_string():
    from backend.core.config import get_settings
    settings = get_settings()
    assert isinstance(settings.elevenlabs_api_key, str)


# ═══════════════════════════════════════════════════════════════════
# 5. Voice endpoint end-to-end (mocked STT + TTS)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_voice_endpoint_returns_audio_with_mocked_services():
    """
    Sends a small fake WAV file; mocks speech_service and analyze
    so the test is fast and doesn't require real API keys.
    Expected: 200 + Content-Type: audio/mpeg.
    """
    fake_audio = b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 100
    fake_mp3 = b"\xff\xfb" + b"\x00" * 128  # minimal valid-ish MP3 frame

    with (
        patch(
            "backend.services.speech_service.speech_service.speech_to_text",
            new=AsyncMock(return_value="ايه الناقص في المخزن؟"),
        ),
        patch(
            "backend.services.speech_service.speech_service.text_to_speech",
            new=AsyncMock(return_value=fake_mp3),
        ),
        patch(
            "backend.api.v1.m2_voice.analyze_inventory",
            new=AsyncMock(
                return_value=type("Resp", (), {
                    "model_dump": lambda self: {
                        "scan_summary": {"total_products_checked": 5},
                        "alerts": [],
                        "rfq_drafts": [],
                        "pricing_recs": [],
                        "language": "ar-EG",
                    }
                })()
            ),
        ),
    ):
        async with _client() as c:
            r = await c.post(
                "/api/v1/m2/voice",
                files={"audio": ("test.wav", io.BytesIO(fake_audio), "audio/wav")},
                data={"language": "ar-EG"},
            )

    assert r.status_code == 200, r.text[:400]
    assert "audio/mpeg" in r.headers.get("content-type", ""), (
        f"Expected audio/mpeg, got {r.headers.get('content-type')}"
    )


@pytest.mark.anyio
async def test_voice_endpoint_returns_recognized_text_header():
    """X-Recognized-Text header carries the STT transcript (URL-encoded)."""
    fake_audio = b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 100
    fake_mp3 = b"\xff\xfb" + b"\x00" * 128

    with (
        patch(
            "backend.services.speech_service.speech_service.speech_to_text",
            new=AsyncMock(return_value="what is low stock?"),
        ),
        patch(
            "backend.services.speech_service.speech_service.text_to_speech",
            new=AsyncMock(return_value=fake_mp3),
        ),
        patch(
            "backend.api.v1.m2_voice.analyze_inventory",
            new=AsyncMock(
                return_value=type("Resp", (), {
                    "model_dump": lambda self: {
                        "scan_summary": {}, "alerts": [],
                        "rfq_drafts": [], "pricing_recs": [], "language": "en",
                    }
                })()
            ),
        ),
    ):
        async with _client() as c:
            r = await c.post(
                "/api/v1/m2/voice",
                files={"audio": ("q.wav", io.BytesIO(fake_audio), "audio/wav")},
                data={"language": "en"},
            )

    assert r.status_code == 200, r.text[:400]
    assert "x-recognized-text" in r.headers, (
        "Response missing X-Recognized-Text header"
    )


# ═══════════════════════════════════════════════════════════════════
# 6. Frontend component
# ═══════════════════════════════════════════════════════════════════

def test_voice_assistant_panel_component_exists():
    p = Path(__file__).resolve().parents[2] / "frontend/components/m2/VoiceAssistantPanel.tsx"
    assert p.exists(), "VoiceAssistantPanel.tsx not found"
    assert p.stat().st_size > 0, "VoiceAssistantPanel.tsx is empty"


def test_voice_assistant_panel_references_voice_endpoint():
    p = Path(__file__).resolve().parents[2] / "frontend/components/m2/VoiceAssistantPanel.tsx"
    content = p.read_text(encoding="utf-8")
    assert "/m2/voice" in content, (
        "VoiceAssistantPanel.tsx does not reference /m2/voice endpoint"
    )
