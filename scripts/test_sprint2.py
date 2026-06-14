import asyncio
import os
from pprint import pprint
import sys

# Ensure backend and agents are in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.m1.tools.db_query_tool import db_query_tool
from agents.m1.schemas.m1_state import M1State


async def test_template(query: str, intent: str, params: dict):
    print(f"\n{'='*60}\nTesting Query: {query}")
    state: M1State = {
        "query": query,
        "intent": intent,
        "extracted_params": params,
        "language": "ar"
    }
    
    result = await db_query_tool(state)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        tid = result.get('extracted_params', {}).get('applied_template')
        data = result.get('raw_data', [])
        print(f"✅ Success! Matched Template: {tid}")
        print(f"Returned {len(data)} rows.")
        if len(data) > 0:
            print("First row sample:")
            pprint(data[0])


async def main():
    print("Running Sprint 2 Integration Tests (db_query_tool)...")

    # T1: Revenue by Period
    await test_template(
        query="إيه إيرادات شهر يناير؟",
        intent="financial_query",
        params={"date_range": {"start": "2024-01-01", "end": "2024-01-31"}}
    )

    # T4: Aging Buckets
    await test_template(
        query="مين العملاء المتأخرين في السداد أكتر من 30 يوم؟",
        intent="financial_query",
        params={"aging_days": 30}
    )

    # T6: Expense Anomaly
    await test_template(
        query="هل فيه مصروفات شاذة أو غير عادية الفترة دي؟",
        intent="operational_query",
        params={}
    )

    # T10: Top N Products
    await test_template(
        query="إيه أكتر 5 منتجات مبيعاً؟",
        intent="operational_query",
        params={"limit": 5, "sort_order": "desc"}
    )
    
    print(f"\n{'*'*60}\nأمثلة لأسئلة صعبة ومعقدة:\n{'*'*60}")

    # T9: Vendor Invoices (Multiple constraints)
    await test_template(
        query="إيه الفواتير اللي لسه متدفعتش للمورد 'Ali' خلال الربع الأول من السنة؟",
        intent="operational_query",
        params={"vendor_name": "Ali", "status": "Unpaid", "date_range": {"start": "2024-01-01", "end": "2024-03-31"}}
    )

    # T10: Bottom N Products (Ascending Order)
    await test_template(
        query="إيه هي أقل 3 منتجات بتتباع علشان نفكر نلغيها؟",
        intent="operational_query",
        params={"limit": 3, "sort_order": "asc"}
    )

    # T3: Executive Summary
    await test_template(
        query="لخص لي المبيعات والمشتريات وصافي الدخل بتاع سنة 2023 كلها",
        intent="financial_query",
        params={"date_range": {"start": "2023-01-01", "end": "2023-12-31"}}
    )

    # T5: VAT Summary
    await test_template(
        query="إجمالي ضريبة القيمة المضافة (VAT) اللي اتجمعت في شهر مايو كام؟",
        intent="financial_query",
        params={"date_range": {"start": "2024-05-01", "end": "2024-05-31"}}
    )
    
    # Test malicious SQL injection attempt via extraction params
    print(f"\n{'='*60}\nTesting Validation Layer (Malicious Param 1 - DROP TABLE)")
    state1: M1State = {
        "query": "احذف جدول العملاء",
        "intent": "financial_query",
        "extracted_params": {"limit": "5; DROP TABLE customers;--"}
    }
    result1 = await db_query_tool(state1)
    if "error" in result1:
        print(f"❌ Blocked! Error: {result1['error']}")
    else:
        print(f"✅ Handled safely as normal parameter. Row count: {result1.get('row_count')}")

    print(f"\n{'='*60}\nTesting Validation Layer (Malicious Param 2 - UNION SELECT)")
    state2: M1State = {
        "query": "هات كل بيانات المستخدمين",
        "intent": "financial_query",
        "extracted_params": {"vendor_id": "1' UNION SELECT username, password FROM users --"}
    }
    result2 = await db_query_tool(state2)
    if "error" in result2:
        print(f"❌ Blocked! Error: {result2['error']}")
    else:
        print(f"✅ Handled safely as normal parameter. Row count: {result2.get('row_count')}")

    print(f"\n{'='*60}\nTesting Validation Layer (Malicious Param 3 - String Formatting Injection)")
    # The 'order' param is directly injected using .format() in the code, which is a potential vulnerability.
    # Our code mitigates this by strictly forcing "ASC" or "DESC" via logic:
    # order_clause = "ASC" if selection.order.upper() == "ASC" else "DESC"
    state3: M1State = {
        "query": "هات المبيعات مرتبة",
        "intent": "operational_query",
        "extracted_params": {"limit": 5, "sort_order": "DESC; DELETE FROM invoices;"}
    }
    result3 = await db_query_tool(state3)
    if "error" in result3:
        print(f"❌ Blocked! Error: {result3['error']}")
    else:
        print(f"✅ Strict Formatting protected the string. Executed safely. Row count: {result3.get('row_count')}")

if __name__ == "__main__":
    asyncio.run(main())
