"""
InvoiceAnalysisToolNode — Sprint 3.

Single LangGraph node that handles the entire invoice_analysis intent
via 4 sequential private methods (no sub-nodes in the graph):

    _extract_invoice_params()   ← GPT-4o-mini  — parameter extraction
    _build_invoice_query()      ← Pure Python   — template selection + SQL params
    _execute_invoice_query()    ← Read-Only DB  — safe execution with AST guard
    _analyze_invoice_data()     ← GPT-4o        — Two-pass analysis + narrative

Blueprint reference: section 2.6 — Invoice Analysis Sub-Pipeline
Sprint plan reference: sprint3_plan.md §4
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

import structlog

from agents.m1.schemas.m1_state import M1State
from agents.m1.tools.invoice_templates import INVOICE_TEMPLATES, SUBTYPE_TO_TEMPLATE
from agents.m1.tools.query_gateway import execute_readonly_query
from agents.prompts.invoice_analysis import (
    INVOICE_NARRATIVE_PROMPT,
    INVOICE_PARAM_EXTRACTION_PROMPT,
)
from agents.shared.llm_client import llm_fast, llm_primary

logger = structlog.get_logger(__name__)

# ── Security: re-use Sprint 2 AST validator ──────────────────────────────────
# Max rows returned by any invoice query
_HARD_LIMIT = 500

# Pattern-detection thresholds (constants — easy to tune)
_OVERDUE_MEDIUM_THRESHOLD = 0.30   # 30% overdue → medium
_OVERDUE_HIGH_THRESHOLD   = 0.50   # 50% overdue → high
_PRICE_CHANGE_MEDIUM      = 0.10   # +10% avg price → medium
_PRICE_CHANGE_HIGH        = 0.25   # +25% avg price → high
_CONCENTRATION_MEDIUM     = 0.40   # single vendor > 40% of total → medium
_CONCENTRATION_HIGH       = 0.60   # single vendor > 60% of total → high


class InvoiceAnalysisToolNode:
    """
    LangGraph-compatible async callable node for invoice analysis.

    Replaces the Sprint 1 ``invoice_analysis_stub``.

    State outputs produced:
        extracted_params : dict  — extended with invoice analysis context
        raw_data         : list  — DB results (serialised dicts)
        narrative        : str   — bilingual LLM narrative
        data_confidence  : float — computed AFTER query execution
    """

    # ── Public entry point ────────────────────────────────────────────────────

    async def __call__(self, state: M1State) -> dict:
        query    = state.get("query", "")
        language = state.get("language", "en")
        prior_params = state.get("extracted_params") or {}

        # ── Step 1: Extract invoice parameters via GPT-4o-mini ──────────────
        invoice_params = await self._extract_invoice_params(query, language, prior_params)

        extraction_confidence = (
            invoice_params
            .get("metrics", {})
            .get("extraction_confidence", 0.0)
        )

        if extraction_confidence < 0.6:
            logger.warning(
                "Invoice param extraction confidence too low — requesting clarification",
                confidence=extraction_confidence,
                query=query,
            )
            return {
                "intent": "clarification_needed",
                "extracted_params": invoice_params,
                "needs_clarification": True,
                "clarification_message": (
                    "يمكنك توضيح تفاصيل أكثر عن الفاتورة أو الفترة الزمنية؟"
                    if language == "ar"
                    else "Could you provide more details about the invoice or time period you're asking about?"
                ),
            }

        # ── Step 2: Build SQL query (pure Python, no LLM) ────────────────────
        sql_obj, sql_params, build_error = self._build_invoice_query(invoice_params)

        if build_error:
            logger.error("Invoice query build failed", error=build_error)
            return {
                "extracted_params": invoice_params,
                "raw_data": [],
                "data_confidence": 0.0,
                "error": build_error,
            }

        # Record which template was applied
        applied_template = sql_params.get("_template_name")
        invoice_params["intent_details"]["applied_template"] = applied_template
        invoice_params["metrics"]["requires_vendor_lookup"]  = sql_params.pop("_vendor_lookup", False)
        sql_params.pop("_template_name", None)

        # ── Step 3: Execute query against read-only DB ───────────────────────
        raw_data, exec_error, query_artifact = await self._execute_invoice_query(
            sql_obj,
            sql_params,
            purpose=str(applied_template or "invoice_analysis"),
        )

        # data_confidence is a POST-QUERY calculation — separate from extraction_confidence
        if exec_error:
            data_confidence = 0.0
        elif len(raw_data) == 0:
            data_confidence = 0.5  # Successful query, no data — graceful empty
        else:
            data_confidence = 1.0

        # ── Step 4: Two-pass analysis + narrative (GPT-4o) ───────────────────
        narrative, analysis_result = await self._analyze_invoice_data(
            raw_data, invoice_params, language
        )
        invoice_params["metrics"]["anomaly_detected"] = analysis_result.get("anomaly_detected", False)

        return {
            "extracted_params": invoice_params,
            "raw_data": raw_data,
            "narrative": narrative,
            "data_confidence": data_confidence,
            "query_mode": "template",
            "matched_template": str(applied_template or ""),
            "query_artifacts": state.get("query_artifacts", []) + [query_artifact],
        }

    # ── Private: Step 1 ──────────────────────────────────────────────────────

    async def _extract_invoice_params(
        self,
        query: str,
        language: str,
        prior_params: dict,
    ) -> dict:
        """
        Call GPT-4o-mini with the bilingual extraction prompt.
        Returns the full extracted_params structure defined in sprint3_plan.md §4.2.
        Falls back to a safe default dict on any LLM/parse failure.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        prompt = INVOICE_PARAM_EXTRACTION_PROMPT.format(
            current_date=current_date,
            language=language,
            query=query,
        )

        try:
            response = await llm_fast.ainvoke(prompt)
            raw_content: str = response.content if hasattr(response, "content") else str(response)

            # Strip markdown code fences if present
            cleaned = re.sub(r"```(?:json)?\s*", "", raw_content).strip().rstrip("`")
            params: dict = json.loads(cleaned)
        except Exception as exc:
            logger.error("Invoice param extraction LLM call failed", error=str(exc))
            # Return a safe default that triggers clarification
            return {
                "domain": "invoice_analysis",
                "intent_details": {
                    "analysis_type": "batch_analysis",
                    "subtype": "totals",
                    "applied_template": None,
                },
                "filters": {
                    "start_date": None,
                    "end_date": None,
                    "vendor_name": None,
                    "vendor_id": None,
                    "invoice_display_id": None,
                    "limit": 10,
                },
                "metrics": {
                    "extraction_confidence": 0.0,
                    "requires_vendor_lookup": False,
                    "anomaly_detected": False,
                },
            }

        # Merge prior intent-classifier params for any fields the extraction prompt missed
        if prior_params:
            filters = params.setdefault("filters", {})
            if not filters.get("start_date") and prior_params.get("date_range", {}).get("start"):
                filters["start_date"] = prior_params["date_range"]["start"]
            if not filters.get("end_date") and prior_params.get("date_range", {}).get("end"):
                filters["end_date"] = prior_params["date_range"]["end"]
            if not filters.get("vendor_name") and prior_params.get("vendor_id"):
                filters["vendor_name"] = prior_params["vendor_id"]

        logger.info(
            "Invoice params extracted",
            analysis_type=params.get("intent_details", {}).get("analysis_type"),
            confidence=params.get("metrics", {}).get("extraction_confidence"),
        )
        return params

    # ── Private: Step 2 ──────────────────────────────────────────────────────

    def _build_invoice_query(
        self, invoice_params: dict
    ) -> tuple[Any, dict, str | None]:
        """
        Selects the right SQL template and builds the parameter dict.
        Returns (sql_text_obj, params_dict, error_str_or_None).

        Vendor partial-match logic:
            If vendor_name is present but vendor_id is absent,
            the name is wrapped in '%..%' for LIKE matching.
        """
        intent_details = invoice_params.get("intent_details", {})
        filters        = invoice_params.get("filters", {})

        analysis_type = intent_details.get("analysis_type", "batch_analysis")
        subtype       = intent_details.get("subtype", "totals")

        # ── Template selection ────────────────────────────────────────────────
        if analysis_type == "single_invoice":
            template_name = "SINGLE_INVOICE_DETAIL"
        else:
            template_name = SUBTYPE_TO_TEMPLATE.get(subtype, "INVOICE_TOTALS_BY_DATE")

        sql_obj = INVOICE_TEMPLATES.get(template_name)
        if sql_obj is None:
            return None, {}, f"Unknown template: {template_name}"

        # ── Build SQL params ──────────────────────────────────────────────────
        current_date = datetime.now().strftime("%Y-%m-%d")

        start_date_str = filters.get("start_date") or "2000-01-01"
        end_date_str   = filters.get("end_date")   or current_date
        as_of_date_str = current_date

        def _to_date(s: str) -> date:
            try:
                return datetime.strptime(s, "%Y-%m-%d").date()
            except ValueError:
                return datetime.now().date()

        vendor_name    = filters.get("vendor_name")
        vendor_id      = filters.get("vendor_id")
        vendor_lookup  = False

        # Wrap vendor_name in % for partial LIKE matching
        if vendor_name and not vendor_id:
            vendor_name  = f"%{vendor_name}%"
            vendor_lookup = True

        params: dict = {
            "start_date":         _to_date(start_date_str),
            "end_date":           _to_date(end_date_str),
            "as_of_date":         _to_date(as_of_date_str),
            "vendor_name":        vendor_name,
            "vendor_id":          vendor_id,
            "invoice_display_id": filters.get("invoice_display_id"),
            "limit":              int(filters.get("limit") or 10),
            # Internal metadata — stripped before DB execution
            "_template_name":     template_name,
            "_vendor_lookup":     vendor_lookup,
        }

        logger.info("Invoice query built", template=template_name, vendor_lookup=vendor_lookup)
        return sql_obj, params, None

    # ── Private: Step 3 ──────────────────────────────────────────────────────

    async def _execute_invoice_query(
        self,
        sql_obj: Any,
        sql_params: dict,
        *,
        purpose: str = "invoice_analysis",
    ) -> tuple[list, str | None, dict]:
        """
        Execute the pre-built SQL against the read-only database.

        Security layers:
          1. AST validation (SELECT-only)
          2. read-only DB user (erp_readonly)
          3. LIMIT 500 enforced
          4. Table whitelist checked via AST (if sqlglot available)
        """
        # Strip internal metadata keys before handing to DB
        clean_params = {k: v for k, v in sql_params.items() if not k.startswith("_")}

        sql_str: str = sql_obj.text if hasattr(sql_obj, "text") else str(sql_obj)

        data, artifact = await execute_readonly_query(
            sql=sql_str,
            parameters=clean_params,
            source="template",
            purpose=purpose,
            hard_limit=_HARD_LIMIT,
        )
        if artifact.get("execution_status") != "success":
            error_message = artifact.get(
                "error_message",
                "Invoice query failed validation or execution.",
            )
            logger.warning(
                "Invoice query rejected",
                category=artifact.get("error_category"),
                error=error_message,
            )
            return [], error_message, artifact

        logger.info("Invoice query executed", row_count=len(data))
        return data, None, artifact

    # ── Private: Step 4 ──────────────────────────────────────────────────────

    async def _analyze_invoice_data(
        self,
        raw_data: list,
        invoice_params: dict,
        language: str,
    ) -> tuple[str, dict]:
        """
        Two-pass analysis:
          Pass 1 (Python)  — compute pre_computed_metrics + detect patterns
          Pass 2 (GPT-4o)  — generate bilingual narrative from metrics + patterns
        """
        # ── Pass 1: Python pre-computation ───────────────────────────────────
        pre_computed, detected_patterns = self._compute_metrics(raw_data, invoice_params)

        # Graceful empty result
        if not raw_data:
            empty_msg = (
                "لا توجد بيانات فواتير مطابقة للمعايير المحددة."
                if language == "ar"
                else "No invoice data found for the specified criteria."
            )
            return empty_msg, {"anomaly_detected": False}

        # ── Pass 2: LLM narrative generation ─────────────────────────────────
        intent_details = invoice_params.get("intent_details", {})
        analysis_type  = intent_details.get("analysis_type", "batch_analysis")
        subtype        = intent_details.get("subtype", "")

        # Summarize raw_data (cap at 20 rows for prompt efficiency)
        data_sample = raw_data[:20]
        raw_data_summary = json.dumps(data_sample, ensure_ascii=False, default=str)

        prompt = INVOICE_NARRATIVE_PROMPT.format(
            query=invoice_params.get("filters", {}).get("invoice_display_id", "")
                  or str(invoice_params.get("filters", {})),
            language=language,
            analysis_type=analysis_type,
            subtype=subtype,
            pre_computed_metrics=json.dumps(pre_computed, ensure_ascii=False, default=str),
            raw_data_summary=raw_data_summary,
            detected_patterns=json.dumps(detected_patterns, ensure_ascii=False),
        )

        try:
            response     = await llm_primary.ainvoke(prompt)
            raw_content: str = response.content if hasattr(response, "content") else str(response)

            cleaned = re.sub(r"```(?:json)?\s*", "", raw_content).strip().rstrip("`")
            analysis_result: dict = json.loads(cleaned)

        except Exception as exc:
            logger.error("Invoice narrative generation failed", error=str(exc))
            fallback_narrative = (
                "تم استرجاع البيانات بنجاح. يُرجى مراجعة النتائج أدناه."
                if language == "ar"
                else "Data retrieved successfully. Please review the results below."
            )
            return fallback_narrative, {"anomaly_detected": False}

        narrative = analysis_result.get("narrative", "")
        logger.info(
            "Invoice narrative generated",
            anomaly=analysis_result.get("anomaly_detected"),
            severity=analysis_result.get("anomaly_severity"),
        )
        return narrative, analysis_result

    # ── Pass 1 helper: Python pre-computation ─────────────────────────────────

    def _compute_metrics(
        self, raw_data: list, invoice_params: dict
    ) -> tuple[dict, list]:
        """
        Compute aggregate metrics and detect patterns entirely in Python.
        Returns (pre_computed_dict, detected_patterns_list).
        """
        if not raw_data:
            return {}, []

        pre_computed   : dict = {}
        detected_patterns: list = []

        # ── Total spend ───────────────────────────────────────────────────────
        amounts = [
            float(r.get("total_amount") or r.get("total_cost") or r.get("monthly_cost") or 0)
            for r in raw_data
        ]
        total_spend = sum(amounts)
        pre_computed["total_spend"]      = round(total_spend, 2)
        pre_computed["record_count"]     = len(raw_data)
        pre_computed["avg_amount"]       = round(total_spend / len(raw_data), 2) if raw_data else 0

        # ── Overdue detection ─────────────────────────────────────────────────
        overdue_statuses = {"unpaid", "overdue", "partial"}
        overdue_rows = [
            r for r in raw_data
            if str(r.get("payment_status", "")).lower() in overdue_statuses
        ]
        overdue_ratio = len(overdue_rows) / len(raw_data) if raw_data else 0
        pre_computed["overdue_count"] = len(overdue_rows)
        pre_computed["overdue_ratio"] = round(overdue_ratio, 3)

        if overdue_ratio >= _OVERDUE_HIGH_THRESHOLD:
            detected_patterns.append({
                "type":        "payment_delays",
                "severity":    "high",
                "description": f"{overdue_ratio:.0%} of invoices are overdue/unpaid",
            })
        elif overdue_ratio >= _OVERDUE_MEDIUM_THRESHOLD:
            detected_patterns.append({
                "type":        "payment_delays",
                "severity":    "medium",
                "description": f"{overdue_ratio:.0%} of invoices are overdue/unpaid",
            })

        # ── Concentration risk (top vendor dominance) ─────────────────────────
        vendor_spend: dict[str, float] = {}
        for r in raw_data:
            vname = r.get("vendor_name") or r.get("name") or "Unknown"
            spend = float(r.get("total_cost") or r.get("total_amount") or r.get("monthly_cost") or 0)
            vendor_spend[vname] = vendor_spend.get(vname, 0) + spend

        if total_spend > 0 and vendor_spend:
            top_vendor      = max(vendor_spend, key=lambda k: vendor_spend[k])
            top_vendor_share = vendor_spend[top_vendor] / total_spend
            pre_computed["top_vendor"]       = top_vendor
            pre_computed["top_vendor_share"] = round(top_vendor_share, 3)

            if top_vendor_share >= _CONCENTRATION_HIGH:
                detected_patterns.append({
                    "type":        "concentration_risk",
                    "severity":    "high",
                    "description": f"{top_vendor} accounts for {top_vendor_share:.0%} of total spend",
                })
            elif top_vendor_share >= _CONCENTRATION_MEDIUM:
                detected_patterns.append({
                    "type":        "concentration_risk",
                    "severity":    "medium",
                    "description": f"{top_vendor} accounts for {top_vendor_share:.0%} of total spend",
                })

        # ── Month-over-month trend (price increase detection) ─────────────────
        monthly_costs = [
            float(r.get("monthly_cost") or r.get("total_spend") or 0)
            for r in raw_data
            if r.get("monthly_cost") is not None or r.get("total_spend") is not None
        ]
        if len(monthly_costs) >= 2:
            first_half_avg = sum(monthly_costs[: len(monthly_costs) // 2]) / (len(monthly_costs) // 2)
            second_half_avg = sum(monthly_costs[len(monthly_costs) // 2 :]) / (
                len(monthly_costs) - len(monthly_costs) // 2
            )
            if first_half_avg > 0:
                change_pct = (second_half_avg - first_half_avg) / first_half_avg
                pre_computed["cost_change_pct"] = round(change_pct, 3)
                if change_pct >= _PRICE_CHANGE_HIGH:
                    detected_patterns.append({
                        "type":        "price_increase",
                        "severity":    "high",
                        "description": f"Spend increased {change_pct:.0%} in recent period vs earlier period",
                    })
                elif change_pct >= _PRICE_CHANGE_MEDIUM:
                    detected_patterns.append({
                        "type":        "price_increase",
                        "severity":    "medium",
                        "description": f"Spend increased {change_pct:.0%} in recent period vs earlier period",
                    })

        pre_computed["patterns_detected"] = len(detected_patterns)
        return pre_computed, detected_patterns


# ── Module-level instance — imported by m1_graph.py ──────────────────────────
invoice_analysis_tool = InvoiceAnalysisToolNode()
