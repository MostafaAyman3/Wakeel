"""
M3 Mock Data Seed Script — loads mock data from real DB tables into memory cache.

Usage:
    python scripts/seed_m3_mock_data.py

This script populates the in-memory mock data stores for M3:
  - order_status     from orders + order_items
  - shipping         from shipments
  - customer_history from customer_interactions
  - Adds test scenario data (repeat issues, etc.)

Run once before testing M3 scenarios.
Output: confirms data loaded and saved.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import structlog

from agents.m3.data.mock_data import ensure_loaded, is_loaded, get_all_order_status

logger = structlog.get_logger(__name__)


async def main():
    print("=" * 60)
    print("M3 Mock Data Seed Script")
    print("=" * 60)

    print("\nLoading mock data from real DB tables...")
    await ensure_loaded()

    if is_loaded():
        status_count = len(get_all_order_status())
        print(f"  ✓ order_status records:  {status_count}")
        print(f"  ✓ Mock data loaded successfully")
    else:
        print("  ✗ Failed to load mock data")
        sys.exit(1)

    print("\nDone. M3 mock data ready for Sprint 1+ testing.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
