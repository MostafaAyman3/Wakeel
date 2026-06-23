"""Controlled response for requests outside current M1 scope."""

from __future__ import annotations

from agents.m1.schemas.m1_state import M1State


async def t5_out_of_scope(state: M1State) -> dict:
    language = state.get("language", "en")
    narrative = (
        "الطلب ده خارج نطاق التحليل الحالي لوكيل. أقدر أحلل البيانات التاريخية "
        "للمبيعات والمصروفات والتحصيل والمخزون والفواتير، لكن التنبؤات المستقبلية "
        "والموضوعات غير المتعلقة ببيانات الأعمال غير متاحة حاليًا."
        if language == "ar"
        else "That request is outside Wakeel's current analytics scope. I can "
        "analyze historical sales, expenses, collections, inventory, and invoices, "
        "but forecasting and unrelated topics are not currently supported."
    )
    return {
        "query_mode": "none",
        "output_format": "direct_text",
        "narrative": narrative,
        "final_response": {
            "format": "direct_text",
            "data": None,
            "chart_config": None,
            "narrative": narrative,
            "alert": None,
            "disclaimer": None,
        },
    }

