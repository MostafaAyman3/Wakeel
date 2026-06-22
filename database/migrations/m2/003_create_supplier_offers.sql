-- Migration: 003_create_supplier_offers
-- Module:     M2 Purchasing & Inventory Agent — Phase 2
-- Sprint:     0 (schema defined upfront; table activated in Sprint 6)
-- Depends on: rfqs (002), vendors
--
-- Purpose:
--   Stores supplier quotes received in response to a sent RFQ.
--   When offers arrive (via POST /api/v1/m2/offers), they are inserted
--   here and the LangGraph is resumed on the stored thread_id to run
--   OfferAnalysisNode.
--
--   For the Sprint 3 MVP demo, offers are entered manually through a
--   form on the Dashboard (mock/hybrid approach). In production, they
--   would be parsed from incoming supplier emails via n8n.
--
-- Run idempotently:
--   psql $DATABASE_URL -f 003_create_supplier_offers.sql

CREATE TABLE IF NOT EXISTS supplier_offers (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Which RFQ this offer responds to.
    rfq_id          UUID        NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,

    -- Which vendor sent this offer (matches vendors.id uuid PK).
    vendor_id       UUID        NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,

    -- Pricing details.
    price_per_unit  NUMERIC(12,2) NOT NULL CHECK (price_per_unit > 0),

    -- Computed: price_per_unit * rfqs.quantity.
    -- Stored for quick comparison in OfferAnalysisNode without re-joining.
    total_price     NUMERIC(12,2),

    -- How many days from order to delivery (vendor's commitment).
    lead_time_days  INTEGER CHECK (lead_time_days > 0),

    -- Payment terms string from the supplier, e.g. "Net 30", "50% upfront".
    payment_terms   VARCHAR(100),

    -- Any extra conditions or notes from the supplier.
    notes           TEXT,

    -- The raw original message (email body / form input) for audit trail.
    raw_message     TEXT,

    received_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Indexes ───────────────────────────────────────────────────────

-- All offers for a given RFQ (OfferAnalysisNode fetches these in bulk)
CREATE INDEX IF NOT EXISTS idx_supplier_offers_rfq
    ON supplier_offers(rfq_id);

-- Offers by vendor (supplier performance dashboard — future)
CREATE INDEX IF NOT EXISTS idx_supplier_offers_vendor
    ON supplier_offers(vendor_id);
