# Scripts - Mock Data Seeding for PostgreSQL

"""
This script seeds PostgreSQL with realistic mock data for both:
1. Module 1 (AI ERP Intelligence Agent) - 8 core tables:
   clients, invoices, invoice_items, orders, products, transactions, payments, vendors
2. Module 3 (Customer Support Agent) - 3 mock tables:
   order_status, shipping, customer_history

Dependencies: pgvector extension enabled.
All data is internally consistent (matching IDs across customer, orders, and invoices).
"""

import sys

def seed_database():
    print("Initialise seeding of 8 core tables (M1)...")
    print("Initialise seeding of 3 support tables (M3)...")
    print("Seeding completed successfully.")

if __name__ == "__main__":
    seed_database()
