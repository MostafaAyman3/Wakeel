"""
M2 Purchasing & Inventory Agent — LangGraph State Schema.

Blueprint reference: M2_Sprints.md §4 — LangGraph State Schema.
Sprint 0 (Architecture) implementation.

All fields use total=False so each node returns only the keys it updates.
The API endpoint (POST /api/v1/m2/analyze) sets the initial defaults
before handing state to the graph.

Detection type drives the routing decision inside InventoryCheckNode:
  low_stock / predicted_shortage  →  Procurement path
  slow_moving / near_expiry       →  Pricing path
"""

from __future__ import annotations

from typing import Literal, TypedDict

# ── Enum-like Literals ────────────────────────────────────────────

TriggerSource = Literal["cron", "manual", "voice"]
"""
Who started this analysis run:
  cron   — n8n daily scheduled job
  manual — user pressed "Scan Now" on the dashboard
  voice  — user asked a voice question via VoiceAssistantPanel
"""

DetectionType = Literal[
    "low_stock",
    "predicted_shortage",
    "slow_moving",
    "near_expiry",
]
"""
What kind of inventory problem was detected for the current product.
InventoryCheckNode sets this field; the graph router reads it
to decide which downstream node to call next.

  low_stock          — quantity <= reorder_point (immediate deficit)
  predicted_shortage — quantity > reorder_point BUT
                       days_until_stockout < lead_time_days
                       (will run out before the next shipment arrives)
  slow_moving        — turnover_rate < SLOW_MOVING_THRESHOLD
                       (capital locked in stagnant stock)
  near_expiry        — expiry_date is within NEAR_EXPIRY_WINDOW days
                       (risk of waste / write-off)
"""

ApprovalStatus = Literal["pending", "approved", "rejected"]
"""Human approval gate result (HumanApprovalNode / interrupt pattern)."""

Language = Literal["ar-EG", "en"]
"""
Output language for all LLM-generated text (alerts, RFQ draft, offer analysis).
Detected from user_context or the incoming request header.
"""


# ── Main State ────────────────────────────────────────────────────

class M2State(TypedDict, total=False):
    """
    Complete state for one M2 analysis run through the LangGraph.

    A single run handles ONE product at a time (current_product).
    The orchestrator loops over flagged_products externally or the
    graph iterates via a map-reduce pattern (Sprint 2+).

    Fields are grouped by pipeline stage:
      Trigger       — how and why this run started
      Scan          — inventory scan output (list of problems found)
      Current       — the single product being processed right now
      Detection     — computed metrics for the current product
      Procurement   — RFQ draft & async loop fields
      Pricing       — pricing recommendation fields
      Offers        — incoming supplier offers & analysis
      Approval      — human-in-the-loop gate state
      Output        — final structured response
      Error         — error propagation
    """

    # ── Trigger ───────────────────────────────────────────────────
    trigger_source: TriggerSource
    """Origin of this analysis run (cron / manual / voice)."""

    trigger_user_id: str
    """UUID of the user or service account that initiated the run."""

    # ── Scan Results ──────────────────────────────────────────────
    flagged_products: list
    """
    All products that failed the inventory check, returned by
    InventoryCheckNode on its first pass.

    Each element is a dict:
    {
      product_id:   str (UUID),
      sku:          str,
      name:         str,
      name_ar:      str,
      category:     str,
      quantity:     int,
      reorder_point: int,
      lead_time_days: int,
      avg_daily_sales: float,
      expiry_date:  str | None,   # ISO date string
      detection_type: DetectionType,
    }
    """

    scan_summary: dict
    """
    High-level counts from the scan pass:
    {
      total_products_checked: int,
      low_stock_count:        int,
      predicted_shortage_count: int,
      slow_moving_count:      int,
      near_expiry_count:      int,
      scanned_at:             str,   # ISO datetime
    }
    """

    # ── Current Product Being Processed ───────────────────────────
    current_product: dict
    """
    The product actively being processed by the downstream nodes.
    Copied from flagged_products one at a time.
    Same schema as a flagged_products element (see above).
    """

    detection_type: DetectionType
    """
    The specific problem type for current_product.
    Set by InventoryCheckNode, read by the graph router to decide
    which path to take (Procurement vs Pricing).
    """

    # ── Computed Metrics (for current_product) ────────────────────
    consumption_rate: float
    """
    Average daily sales (units/day) for the current product,
    derived from order_items over the last 90 days.
    Same as avg_daily_sales stored in the inventory table.
    """

    turnover_rate: float
    """
    Inventory turnover = total_sold / avg_inventory_level over last 90 days.
    Low value (<0.5/month) → slow_moving flag.
    """

    days_until_stockout: float
    """
    Estimated days before stock hits zero at current consumption rate:
      days_until_stockout = current_quantity / avg_daily_sales
    Triggers predicted_shortage when this < lead_time_days.
    """

    suggested_quantity: int
    """
    Recommended purchase quantity, computed by InventoryCheckNode:
      max(reorder_point * 2 - current_quantity, min_order_qty)
    Used by RFQBuilderNode as the default quantity in the draft email.
    """

    explanation: str
    """
    One-sentence plain-language reason for the alert (used by
    AlertGeneratorNode as context and by the Dashboard tooltip).
    """

    # ── Procurement Path Fields ───────────────────────────────────
    rfq_draft: str
    """
    Full text of the Request-For-Quotation email draft,
    generated by RFQBuilderNode in the user's language.
    """

    rfq_id: str
    """
    UUID of the rfqs row created in the DB when the RFQ is saved.
    Passed to HumanApprovalNode and OfferAnalysisNode.
    """

    thread_id: str
    """
    LangGraph / AsyncPostgresSaver checkpoint key for this run.
    Format: "m2-rfq-{rfq_id}".
    The graph is paused here after the RFQ is sent; when supplier
    offers arrive (POST /api/v1/m2/offers), the same thread_id is
    used to resume the graph from OfferAnalysisNode.
    """

    # ── Pricing Path Fields ───────────────────────────────────────
    pricing_recommendation: str
    """
    LLM-generated pricing advice from PricingAdvisorNode,
    e.g. "خفّض السعر بنسبة 15% لتسريع تصريف المخزون قبل انتهاء الصلاحية".
    Stored in the pricing_recommendations view on the Dashboard.
    """

    # ── Supplier Offers (Phase 2) ─────────────────────────────────
    supplier_offers: list
    """
    List of offer dicts received from suppliers for the current RFQ:
    [
      {
        offer_id:       str (UUID),
        vendor_id:      str (UUID),
        vendor_name:    str,
        price_per_unit: float,
        total_price:    float,
        lead_time_days: int,
        payment_terms:  str,
        notes:          str,
      },
      ...
    ]
    """

    recommended_offer: dict
    """
    The single best offer selected by OfferAnalysisNode with its reasoning:
    {
      offer_id:     str (UUID),
      vendor_name:  str,
      reason:       str,   # LLM-generated justification (language-aware)
      score:        float, # composite score (price 50% + lead_time 30% + terms 20%)
    }
    """

    # ── Human Approval Gate ───────────────────────────────────────
    approval_status: ApprovalStatus
    """
    Result of the HumanApprovalNode interrupt.
    The graph is paused (interrupt) until the user clicks
    "Approve" or "Reject" on the Dashboard, which calls
    POST /api/v1/m2/rfqs/{id}/approve with status in the body.
    """

    approval_notes: str
    """Optional free-text note the user adds when approving/rejecting."""

    # ── Output ────────────────────────────────────────────────────
    alerts_generated: list
    """
    List of inventory_alerts rows saved to DB during this run:
    [{ alert_id, product_id, alert_type, message, metadata }, ...]
    Returned in the API response for the Dashboard to render.
    """

    final_response: dict
    """
    Structured response returned by POST /api/v1/m2/analyze:
    {
      scan_summary:      dict,
      alerts:            list,
      rfq_drafts:        list,   # one per procurement-path product
      pricing_recs:      list,   # one per pricing-path product
      language:          str,
    }
    """

    # ── User / Session Context ────────────────────────────────────
    user_context: dict
    """
    Caller context passed from the API layer:
    {
      user_id:   str (UUID),
      role:      str,            # "manager" | "procurement_officer" | "admin"
      language:  Language,       # "ar-EG" | "en"
    }
    All LLM nodes read user_context["language"] to choose output language.
    """

    # ── Error Propagation ─────────────────────────────────────────
    error: str
    """Non-empty string means a node failed; downstream nodes skip processing."""
