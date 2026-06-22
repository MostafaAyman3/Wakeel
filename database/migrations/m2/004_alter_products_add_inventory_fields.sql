-- Migration: 004_alter_inventory_add_m2_fields
-- Module:     M2 Purchasing & Inventory Agent
-- Sprint:     0 (Architecture & Planning)
-- Depends on: inventory table (already exists in public schema)
--
-- Purpose:
--   The existing `inventory` table tracks quantity and reorder_point.
--   M2 needs three additional fields to support its detection algorithms:
--
--   lead_time_days  — how many days it takes to receive stock after ordering.
--                     Used in predicted_shortage: if days_until_stockout
--                     < lead_time_days, we'll run out before the next
--                     shipment arrives even though we're above reorder_point.
--                     Default 7 days (conservative estimate).
--
--   expiry_date     — for perishable / dated products (Phase 1 near_expiry).
--                     NULL for non-expiring products (electronics, furniture).
--                     The seed script populates this for demo scenarios.
--
--   avg_daily_sales — rolling average of units sold per day (last 90 days).
--                     Computed from order_items history; stored here as a
--                     cached value updated nightly (or on each /analyze run).
--                     Used for: days_until_stockout and turnover_rate.
--                     Default 0 (means "unknown" — InventoryCheckNode
--                     recalculates on the fly if this is 0).
--
-- NOTE: We add these to `inventory` (not `products`) because they are
--       operational/logistics fields that belong to the inventory record,
--       not to the product definition itself.
--
-- Run idempotently:
--   psql $DATABASE_URL -f 004_alter_inventory_add_m2_fields.sql

-- ── 1. Add new columns (IF NOT EXISTS — safe to re-run) ───────────
ALTER TABLE inventory
    ADD COLUMN IF NOT EXISTS lead_time_days   INTEGER      DEFAULT 7
        CHECK (lead_time_days > 0),
    ADD COLUMN IF NOT EXISTS expiry_date      DATE,
    ADD COLUMN IF NOT EXISTS avg_daily_sales  NUMERIC(10,2) DEFAULT 0
        CHECK (avg_daily_sales >= 0);

-- ── 2. Indexes ─────────────────────────────────────────────────────

-- Near-expiry query: "find products expiring within N days"
-- Partial index: only indexes rows that actually have an expiry date.
CREATE INDEX IF NOT EXISTS idx_inventory_expiry_date
    ON inventory(expiry_date)
    WHERE expiry_date IS NOT NULL;

-- Predicted shortage query: "find products where stock / avg_daily_sales < lead_time_days"
-- A composite index helps the InventoryCheckNode SQL filter efficiently.
CREATE INDEX IF NOT EXISTS idx_inventory_m2_check
    ON inventory(quantity, reorder_point, avg_daily_sales, lead_time_days);

-- ── 3. Comment the new columns for documentation ──────────────────
COMMENT ON COLUMN inventory.lead_time_days  IS 'Days from order placement to delivery. Used for predicted_shortage detection.';
COMMENT ON COLUMN inventory.expiry_date     IS 'Product batch expiry date. NULL for non-perishable items. Used for near_expiry detection.';
COMMENT ON COLUMN inventory.avg_daily_sales IS 'Cached average daily sales (units/day) over last 90 days. Updated by InventoryCheckNode on each /analyze run.';
