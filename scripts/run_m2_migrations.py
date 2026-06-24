import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from backend.core.database import engine

async def run_migrations():
    load_dotenv()
    
    migration_dir = Path("database/migrations/m2")
    files = [
        "001_create_inventory_alerts.sql",
        "002_create_rfqs.sql",
        "003_create_supplier_offers.sql",
        "004_alter_products_add_inventory_fields.sql",
        "005_create_pricing_recommendations.sql"
    ]
    
    async with engine.begin() as conn:
        from sqlalchemy import text
        for file in files:
            file_path = migration_dir / file
            print(f"Running migration: {file}")
            sql = file_path.read_text(encoding="utf-8")
            # asyncpg requires the raw driver connection for multi-statement execution
            raw_conn = await conn.get_raw_connection()
            await raw_conn.driver_connection.execute(sql)
            
    print("M2 Migrations completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_migrations())
