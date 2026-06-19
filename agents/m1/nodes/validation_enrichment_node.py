"""
ValidationEnrichmentNode — validates retrieved data and enriches state.

Blueprint reference: Sprint 1 spec — "يتحقق من اكتمال البيانات المُسترجعة ويُثريها بالسياق"

Sprint 5 upgrade:
  • Data confidence scoring.
  • Proactive Anomaly Detection — pure Python thresholds (no LLM call).
  • Sets anomaly_detected + anomaly_details in state for downstream nodes.
  • Confidence-based routing: data_confidence < 0.70 → clarification.
"""

from __future__ import annotations

from typing import Any

import structlog

from agents.m1.schemas.m1_state import M1State

logger = structlog.get_logger(__name__)

# ── Anomaly thresholds (pure Python — no LLM call) ───────────────────────────
_ANOMALY_MULTIPLIER = 2.0   # Value > 2x average → anomaly
_MIN_ROWS_FOR_ANOMALY = 3   # Need at least 3 data points to detect anomalies


async def validate_and_enrich(state: M1State) -> dict:
    """Validate and enrich the data in the current state.

    Sprint 5: full anomaly detection + confidence routing.
    """
    raw_data: list = state.get("raw_data", [])
    intent: str = state.get("intent", "unknown")
    existing_confidence: float = state.get("data_confidence", -1.0)
    extracted_params: dict = state.get("extracted_params", {})
    language: str = state.get("language", "en")

    # ── Data-confidence score ─────────────────────────────────────────────
    # If upstream node already set confidence (e.g. invoice_analysis_tool),
    # preserve it; otherwise compute from raw_data presence.
    if existing_confidence >= 0:
        data_confidence = existing_confidence
    else:
        data_confidence = 1.0 if raw_data else 0.0

    # ── Confidence-based routing (M1_Sprints.md Sprint 2) ─────────────────
    if 0 < data_confidence < 0.70:
        logger.warning(
            "validation: low data_confidence → requesting clarification",
            confidence=data_confidence,
        )
        clarification_msg = (
            "النتائج غير مكتملة. هل يمكنك توضيح السؤال أو تحديد الفترة الزمنية؟"
            if language == "ar"
            else "The results are incomplete. Could you clarify the question or specify the time period?"
        )
        return {
            "data_confidence": data_confidence,
            "intent": "clarification_needed",
            "needs_clarification": True,
            "clarification_message": clarification_msg,
        }

    # ── Proactive Anomaly Detection ───────────────────────────────────────
    # Runs on financial_query and operational_query intents.
    # Also picks up anomalies already detected by invoice_analysis_tool.
    anomaly_detected = False
    anomaly_details: dict = {}

    # Check if upstream (invoice_analysis) already flagged an anomaly
    upstream_anomaly = (
        extracted_params.get("metrics", {}).get("anomaly_detected", False)
    )
    if upstream_anomaly:
        anomaly_detected = True
        anomaly_details = {
            "type": "invoice_pattern",
            "severity": "warning",
            "title": "Invoice Pattern Anomaly" if language == "en" else "شذوذ في نمط الفواتير",
            "description": "Upstream invoice analysis detected suspicious patterns.",
            "recommendation": (
                "Review the detailed invoice analysis for more information."
                if language == "en"
                else "راجع تحليل الفواتير التفصيلي لمزيد من المعلومات."
            ),
        }

    # Check template T6 (expense_anomaly) results
    template_id = extracted_params.get("applied_template", "")
    if template_id == "T6" and raw_data:
        anomaly_detected = True
        # Find the worst anomaly in the results
        worst_row = max(raw_data, key=lambda r: float(r.get("amount", 0)))
        avg_amount = float(worst_row.get("avg_amount", 1))
        actual_amount = float(worst_row.get("amount", 0))
        category = worst_row.get("category", "Unknown")
        pct_increase = ((actual_amount - avg_amount) / avg_amount * 100) if avg_amount > 0 else 0

        anomaly_details = {
            "type": "expense_anomaly",
            "severity": "critical" if pct_increase > 200 else "warning",
            "title": (
                f"🔴 مصروف غير معتاد في فئة {category}"
                if language == "ar"
                else f"🔴 Unusual Expense in {category}"
            ),
            "description": (
                f"ارتفاع بنسبة {pct_increase:.0f}% مقارنة بالمتوسط ({avg_amount:,.0f} → {actual_amount:,.0f})"
                if language == "ar"
                else f"{pct_increase:.0f}% increase compared to average ({avg_amount:,.0f} → {actual_amount:,.0f})"
            ),
            "recommendation": (
                "يُنصح بمراجعة الفواتير المرتبطة بهذه الفئة."
                if language == "ar"
                else "Review the invoices associated with this category."
            ),
        }

    # Generic anomaly scan — only for financial/operational queries without
    # template-specific detection already applied.
    if (
        not anomaly_detected
        and intent in ("financial_query", "operational_query")
        and len(raw_data) >= _MIN_ROWS_FOR_ANOMALY
    ):
        anomaly_detected, anomaly_details = _scan_for_generic_anomalies(
            raw_data, language
        )

    logger.info(
        "validation: enrichment complete",
        data_confidence=data_confidence,
        anomaly_detected=anomaly_detected,
        intent=intent,
    )

    result: dict = {
        "data_confidence": data_confidence,
        "anomaly_detected": anomaly_detected,
        "anomaly_details": anomaly_details,
    }

    return result


def _scan_for_generic_anomalies(
    raw_data: list[dict], language: str
) -> tuple[bool, dict]:
    """
    Scan numeric columns for values exceeding 2x the column average.

    Pure Python — no LLM call needed.
    Returns (anomaly_found: bool, details: dict).
    """
    if not raw_data:
        return False, {}

    # Collect numeric columns
    numeric_cols: list[str] = []
    for key, val in raw_data[0].items():
        if isinstance(val, (int, float)):
            numeric_cols.append(key)

    for col in numeric_cols:
        values = [float(row.get(col, 0)) for row in raw_data if row.get(col) is not None]
        if len(values) < _MIN_ROWS_FOR_ANOMALY:
            continue

        avg_val = sum(values) / len(values)
        if avg_val <= 0:
            continue

        max_val = max(values)
        if max_val > avg_val * _ANOMALY_MULTIPLIER:
            pct = ((max_val - avg_val) / avg_val) * 100
            return True, {
                "type": "value_anomaly",
                "severity": "warning",
                "title": (
                    f"قيمة غير معتادة في {col.replace('_', ' ')}"
                    if language == "ar"
                    else f"Unusual value in {col.replace('_', ' ')}"
                ),
                "description": (
                    f"أعلى قيمة ({max_val:,.0f}) تتجاوز المتوسط ({avg_val:,.0f}) بنسبة {pct:.0f}%"
                    if language == "ar"
                    else f"Maximum value ({max_val:,.0f}) exceeds average ({avg_val:,.0f}) by {pct:.0f}%"
                ),
                "recommendation": (
                    "يُنصح بمراجعة هذه القيمة للتحقق من صحتها."
                    if language == "ar"
                    else "Review this value to verify its accuracy."
                ),
            }

    return False, {}
