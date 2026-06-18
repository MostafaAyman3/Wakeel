# Database Schema Reference — AERIE

> **Auto-generated** — لا تعدّل يدوياً. شغّل `scripts/verify_connections.py` لتحديث.
> **Generated at:** 2026-06-18 19:45:54
> **Source:** Supabase (public schema)
> **Total tables:** 15

---

## Table of Contents

- [audit_log](#audit-log)
- [conversations](#conversations)
- [customer_interactions](#customer-interactions)
- [customers](#customers)
- [inventory](#inventory)
- [invoice_items](#invoice-items)
- [invoices](#invoices)
- [order_items](#order-items)
- [orders](#orders)
- [payments](#payments)
- [products](#products)
- [shipments](#shipments)
- [tax_chunks](#tax-chunks)
- [transactions](#transactions)
- [vendors](#vendors)

---

## `audit_log`

**Type:** BASE TABLE | **Rows:** 0 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `entity_type` | `varchar(50)` | NO | `` |  |
| `entity_id` | `uuid` | YES | `` |  |
| `action` | `varchar(50)` | NO | `` |  |
| `details` | `jsonb` | YES | `` |  |
| `performed_by` | `varchar(100)` | YES | `` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

---

## `conversations`

**Type:** BASE TABLE | **Rows:** 0 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `session_id` | `uuid` | NO | `` |  |
| `role` | `varchar(20)` | NO | `` |  |
| `content` | `text` | NO | `` |  |
| `metadata` | `jsonb` | YES | `'{}'::jsonb` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

**Indexes:**

- `idx_conversations_session`: `CREATE INDEX idx_conversations_session ON public.conversations USING btree (session_id)`
- `idx_conversations_created`: `CREATE INDEX idx_conversations_created ON public.conversations USING btree (session_id, created_at)`

---

## `customer_interactions`

**Type:** BASE TABLE | **Rows:** 32 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `customer_id` | `uuid` | NO | `` |  |
| `order_id` | `uuid` | YES | `` |  |
| `interaction_type` | `varchar(30)` | NO | `` |  |
| `issue_type` | `varchar(30)` | YES | `` |  |
| `description` | `text` | YES | `` |  |
| `resolution` | `text` | YES | `` |  |
| `status` | `varchar(20)` | YES | `'Open'::character varying` |  |
| `agent_name` | `varchar(100)` | YES | `` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

**Foreign Keys:**

- `customer_id` → `customers.id`
- `order_id` → `orders.id`

**Indexes:**

- `idx_interactions_customer`: `CREATE INDEX idx_interactions_customer ON public.customer_interactions USING btree (customer_id)`
- `idx_interactions_issue`: `CREATE INDEX idx_interactions_issue ON public.customer_interactions USING btree (issue_type)`

---

## `customers`

**Type:** BASE TABLE | **Rows:** 50 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `display_id` | `varchar(20)` | NO | `` |  |
| `name` | `varchar(200)` | NO | `` |  |
| `name_ar` | `varchar(200)` | YES | `` |  |
| `email` | `varchar(200)` | YES | `` |  |
| `phone` | `varchar(30)` | YES | `` |  |
| `address` | `text` | YES | `` |  |
| `city` | `varchar(100)` | YES | `` |  |
| `tier` | `varchar(20)` | YES | `'Normal'::character varying` |  |
| `lifetime_value` | `numeric` | YES | `0` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

**Indexes:**

- `customers_display_id_key`: `CREATE UNIQUE INDEX customers_display_id_key ON public.customers USING btree (display_id)`
- `customers_email_key`: `CREATE UNIQUE INDEX customers_email_key ON public.customers USING btree (email)`

---

## `inventory`

**Type:** BASE TABLE | **Rows:** 25 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `product_id` | `uuid` | NO | `` |  |
| `quantity` | `integer` | NO | `0` |  |
| `warehouse_location` | `varchar(50)` | YES | `` |  |
| `reorder_point` | `integer` | YES | `10` |  |
| `last_restocked` | `timestamptz` | YES | `` |  |
| `updated_at` | `timestamptz` | YES | `now()` |  |

**Foreign Keys:**

- `product_id` → `products.id`

**Indexes:**

- `idx_inventory_product`: `CREATE INDEX idx_inventory_product ON public.inventory USING btree (product_id)`

---

## `invoice_items`

**Type:** BASE TABLE | **Rows:** 662 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `invoice_id` | `uuid` | NO | `` |  |
| `product_id` | `uuid` | YES | `` |  |
| `description` | `varchar(300)` | YES | `` |  |
| `quantity` | `integer` | NO | `` |  |
| `unit_price` | `numeric` | NO | `` |  |
| `total_price` | `numeric` | NO | `` |  |
| `tax_amount` | `numeric` | YES | `0` |  |

**Foreign Keys:**

- `invoice_id` → `invoices.id`
- `product_id` → `products.id`

**Indexes:**

- `idx_invoice_items_invoice`: `CREATE INDEX idx_invoice_items_invoice ON public.invoice_items USING btree (invoice_id)`

---

## `invoices`

**Type:** BASE TABLE | **Rows:** 318 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `display_id` | `varchar(30)` | NO | `` |  |
| `type` | `varchar(20)` | NO | `` |  |
| `order_id` | `uuid` | YES | `` |  |
| `customer_id` | `uuid` | YES | `` |  |
| `vendor_id` | `uuid` | YES | `` |  |
| `invoice_date` | `timestamptz` | NO | `` |  |
| `total_amount` | `numeric` | NO | `` |  |
| `tax_amount` | `numeric` | YES | `0` |  |
| `due_date` | `timestamptz` | NO | `` |  |
| `payment_status` | `varchar(20)` | YES | `'Unpaid'::character varying` |  |
| `notes` | `text` | YES | `` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

**Foreign Keys:**

- `customer_id` → `customers.id`
- `order_id` → `orders.id`
- `vendor_id` → `vendors.id`

**Indexes:**

- `invoices_display_id_key`: `CREATE UNIQUE INDEX invoices_display_id_key ON public.invoices USING btree (display_id)`
- `idx_invoices_customer`: `CREATE INDEX idx_invoices_customer ON public.invoices USING btree (customer_id)`
- `idx_invoices_vendor`: `CREATE INDEX idx_invoices_vendor ON public.invoices USING btree (vendor_id)`
- `idx_invoices_date`: `CREATE INDEX idx_invoices_date ON public.invoices USING btree (invoice_date)`
- `idx_invoices_status`: `CREATE INDEX idx_invoices_status ON public.invoices USING btree (payment_status)`
- `idx_invoices_type`: `CREATE INDEX idx_invoices_type ON public.invoices USING btree (type)`
- `idx_invoices_display`: `CREATE INDEX idx_invoices_display ON public.invoices USING btree (display_id)`

---

## `order_items`

**Type:** BASE TABLE | **Rows:** 594 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `order_id` | `uuid` | NO | `` |  |
| `product_id` | `uuid` | NO | `` |  |
| `quantity` | `integer` | NO | `` |  |
| `unit_price` | `numeric` | NO | `` |  |
| `total_price` | `numeric` | NO | `` |  |

**Foreign Keys:**

- `order_id` → `orders.id`
- `product_id` → `products.id`

**Indexes:**

- `idx_order_items_order`: `CREATE INDEX idx_order_items_order ON public.order_items USING btree (order_id)`

---

## `orders`

**Type:** BASE TABLE | **Rows:** 250 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `display_id` | `varchar(30)` | NO | `` |  |
| `customer_id` | `uuid` | NO | `` |  |
| `order_date` | `timestamptz` | NO | `` |  |
| `status` | `varchar(30)` | NO | `'Pending'::character varying` |  |
| `total_amount` | `numeric` | NO | `` |  |
| `tax_amount` | `numeric` | YES | `0` |  |
| `estimated_delivery` | `timestamptz` | YES | `` |  |
| `notes` | `text` | YES | `` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

**Foreign Keys:**

- `customer_id` → `customers.id`

**Indexes:**

- `orders_display_id_key`: `CREATE UNIQUE INDEX orders_display_id_key ON public.orders USING btree (display_id)`
- `idx_orders_customer`: `CREATE INDEX idx_orders_customer ON public.orders USING btree (customer_id)`
- `idx_orders_date`: `CREATE INDEX idx_orders_date ON public.orders USING btree (order_date)`
- `idx_orders_status`: `CREATE INDEX idx_orders_status ON public.orders USING btree (status)`
- `idx_orders_display`: `CREATE INDEX idx_orders_display ON public.orders USING btree (display_id)`

---

## `payments`

**Type:** BASE TABLE | **Rows:** 145 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `invoice_id` | `uuid` | NO | `` |  |
| `amount` | `numeric` | NO | `` |  |
| `payment_date` | `timestamptz` | NO | `` |  |
| `payment_method` | `varchar(30)` | YES | `'Bank Transfer'::character varying` |  |
| `reference_number` | `varchar(50)` | YES | `` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

**Foreign Keys:**

- `invoice_id` → `invoices.id`

**Indexes:**

- `idx_payments_invoice`: `CREATE INDEX idx_payments_invoice ON public.payments USING btree (invoice_id)`

---

## `products`

**Type:** BASE TABLE | **Rows:** 25 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `sku` | `varchar(30)` | NO | `` |  |
| `name` | `varchar(200)` | NO | `` |  |
| `name_ar` | `varchar(200)` | YES | `` |  |
| `category` | `varchar(100)` | NO | `` |  |
| `category_ar` | `varchar(100)` | YES | `` |  |
| `unit_price` | `numeric` | NO | `` |  |
| `cost_price` | `numeric` | NO | `` |  |
| `vat_rate` | `numeric` | YES | `14.00` |  |
| `is_active` | `boolean` | YES | `true` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

**Indexes:**

- `products_sku_key`: `CREATE UNIQUE INDEX products_sku_key ON public.products USING btree (sku)`

---

## `shipments`

**Type:** BASE TABLE | **Rows:** 189 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `order_id` | `uuid` | NO | `` |  |
| `tracking_number` | `varchar(30)` | NO | `` |  |
| `carrier` | `varchar(100)` | NO | `` |  |
| `status` | `varchar(30)` | YES | `'Processing'::character varying` |  |
| `current_location` | `varchar(200)` | YES | `` |  |
| `estimated_delivery` | `timestamptz` | YES | `` |  |
| `shipped_date` | `timestamptz` | YES | `` |  |
| `delivered_date` | `timestamptz` | YES | `` |  |
| `updated_at` | `timestamptz` | YES | `now()` |  |

**Foreign Keys:**

- `order_id` → `orders.id`

**Indexes:**

- `idx_shipments_order`: `CREATE INDEX idx_shipments_order ON public.shipments USING btree (order_id)`
- `idx_shipments_tracking`: `CREATE INDEX idx_shipments_tracking ON public.shipments USING btree (tracking_number)`

---

## `tax_chunks`

**Type:** BASE TABLE | **Rows:** 226 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `chunk_id` | `text` | NO | `` |  |
| `document_name` | `text` | NO | `''::text` |  |
| `law_number` | `text` | NO | `''::text` |  |
| `article` | `text` | NO | `''::text` |  |
| `section` | `text` | NO | `''::text` |  |
| `chunk_text` | `text` | NO | `` |  |
| `embedding` | `vector` | YES | `` |  |
| `metadata` | `jsonb` | YES | `'{}'::jsonb` |  |
| `created_at` | `timestamptz` | NO | `now()` |  |

**Indexes:**

- `tax_chunks_chunk_id_key`: `CREATE UNIQUE INDEX tax_chunks_chunk_id_key ON public.tax_chunks USING btree (chunk_id)`
- `tax_chunks_embedding_idx`: `CREATE INDEX tax_chunks_embedding_idx ON public.tax_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists='100')`

---

## `transactions`

**Type:** BASE TABLE | **Rows:** 233 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `type` | `varchar(20)` | NO | `` |  |
| `category` | `varchar(100)` | NO | `` |  |
| `amount` | `numeric` | NO | `` |  |
| `description` | `text` | YES | `` |  |
| `transaction_date` | `timestamptz` | NO | `` |  |
| `reference_type` | `varchar(30)` | YES | `` |  |
| `reference_id` | `uuid` | YES | `` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

**Indexes:**

- `idx_transactions_date`: `CREATE INDEX idx_transactions_date ON public.transactions USING btree (transaction_date)`
- `idx_transactions_type`: `CREATE INDEX idx_transactions_type ON public.transactions USING btree (type)`
- `idx_transactions_category`: `CREATE INDEX idx_transactions_category ON public.transactions USING btree (category)`

---

## `vendors`

**Type:** BASE TABLE | **Rows:** 10 | **PK:** `id`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `uuid` | NO | `gen_random_uuid()` | 🔑 PK |
| `display_id` | `varchar(20)` | NO | `` |  |
| `name` | `varchar(200)` | NO | `` |  |
| `name_ar` | `varchar(200)` | YES | `` |  |
| `contact_email` | `varchar(200)` | YES | `` |  |
| `phone` | `varchar(30)` | YES | `` |  |
| `address` | `text` | YES | `` |  |
| `city` | `varchar(100)` | YES | `` |  |
| `category` | `varchar(100)` | YES | `` |  |
| `payment_terms` | `varchar(50)` | YES | `'Net 30'::character varying` |  |
| `created_at` | `timestamptz` | YES | `now()` |  |

**Indexes:**

- `vendors_display_id_key`: `CREATE UNIQUE INDEX vendors_display_id_key ON public.vendors USING btree (display_id)`

---
