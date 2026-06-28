"""
Quick end-to-end test for n8n Webhook -> Gmail flow.
Updates one vendor's email, runs /analyze, then approves the RFQ.
"""
import asyncio, re
import httpx
import asyncpg
from backend.core.config import get_settings

TARGET_EMAIL = "hgameactivation@gmail.com"
BASE = "http://localhost:8000"

async def run():
    settings = get_settings()
    db_url = re.sub(r"postgresql\+asyncpg", "postgresql", settings.database_url)

    # 1. Update first vendor's contact_email to target
    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    row = await conn.fetchrow(
        "UPDATE vendors SET contact_email = $1 WHERE id = (SELECT id FROM vendors ORDER BY name LIMIT 1) RETURNING name, contact_email",
        TARGET_EMAIL
    )
    await conn.close()
    print(f"OK Updated vendor: {row['name']} -> {row['contact_email']}")

    async with httpx.AsyncClient(timeout=120) as client:
        # 2. Run /analyze to generate fresh RFQ
        print("\n>> Running /analyze ...")
        r = await client.post(f"{BASE}/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
        r.raise_for_status()
        data = r.json()
        drafts = data.get("rfq_drafts", [])
        print(f"   scan_summary: {data['scan_summary']}")
        print(f"   RFQ drafts:   {len(drafts)}")

        if not drafts:
            print("SKIP No RFQ drafts — no low_stock/predicted_shortage products found.")
            return

        rfq_id = drafts[0]["rfq_id"]
        print(f"   RFQ ID: {rfq_id}")

        # 3. Approve the RFQ -> triggers rfq_send_node -> fires n8n webhook
        print("\n>> Approving RFQ ...")
        r2 = await client.post(
            f"{BASE}/api/v1/m2/rfqs/{rfq_id}/approve",
            json={"approval_status": "approved", "notes": "Test — send to n8n"}
        )
        r2.raise_for_status()
        result = r2.json()
        print(f"   approval_status: {result.get('approval_status')}")
        print(f"   sent:            {result.get('sent')}")
        print(f"   message:         {result.get('message')}")
        print(f"\nOK Done — check n8n and {TARGET_EMAIL} inbox!")

asyncio.run(run())
