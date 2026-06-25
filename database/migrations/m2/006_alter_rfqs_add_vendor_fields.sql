-- Migration: 006_alter_rfqs_add_vendor_fields
-- Module:     M2 Purchasing & Inventory Agent
-- Sprint:     9 (n8n Automation & Webhooks)
-- Depends on: 002_create_rfqs.sql
--
-- Purpose:
--   Stores the selected vendor's name and email directly on the rfqs row
--   so that rfq_send_node can include them in the n8n webhook payload
--   without a JOIN at send-time.
--
-- Run idempotently:
--   psql $DATABASE_URL -f 006_alter_rfqs_add_vendor_fields.sql

ALTER TABLE rfqs ADD COLUMN IF NOT EXISTS vendor_email VARCHAR(200);
ALTER TABLE rfqs ADD COLUMN IF NOT EXISTS vendor_name  VARCHAR(200);
