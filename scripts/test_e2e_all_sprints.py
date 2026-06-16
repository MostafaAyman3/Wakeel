import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure environment variables are loaded for LangSmith tracking
from dotenv import load_dotenv
load_dotenv()

from agents.m1.graphs.m1_graph import m1_graph
from agents.m1.schemas.m1_state import M1State

async def test_e2e_flow():
    # Verify LangSmith is enabled
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    project_name = os.getenv("LANGCHAIN_PROJECT", "default")
    print(f"\n[{'✅' if tracing_enabled else '❌'}] LangSmith Tracing is {'ENABLED' if tracing_enabled else 'DISABLED'} (Project: {project_name})")
    if not tracing_enabled:
        print("    --> NOTE: To see logs in LangSmith, set LANGCHAIN_TRACING_V2=true and provide LANGCHAIN_API_KEY in .env")

    tests = [
        # --- Sprint 1: General Flow & Clarification ---
        {
            "name": "[Sprint 1] Clarification Needed",
            "query": "عايز تقرير عن المبيعات",
            "expected_intent": "clarification_needed"
        },
        # --- Sprint 2: DB Query Tool (Operational & Financial) ---
        {
            "name": "[Sprint 2] Operational Query (AR)",
            "query": "كم عدد الطلبات التي تم توصيلها هذا الشهر؟",
            "expected_intent": "operational_query"
        },
        {
            "name": "[Sprint 2] Financial Query (EN)",
            "query": "What is our total revenue for the current quarter?",
            "expected_intent": "financial_query"
        },
        {
            "name": "[Sprint 2] Customer Query (AR)",
            "query": "من هم أعلى 5 عملاء شراءً؟",
            "expected_intent": "financial_query"
        },
        # --- Sprint 3: Invoice Analysis Tool ---
        {
            "name": "[Sprint 3] Single Invoice Lookup (AR)",
            "query": "ما هي تفاصيل الفاتورة INV-0045 وهل هي مدفوعة؟",
            "expected_intent": "invoice_analysis"
        },
        {
            "name": "[Sprint 3] Batch Analysis - Overdue Invoices (EN)",
            "query": "Show me all overdue invoices along with their total amounts.",
            "expected_intent": "invoice_analysis"
        },
        {
            "name": "[Sprint 3] Top Vendors Analysis (AR)",
            "query": "مين هما أكتر 3 موردين بندفعلهم فلوس؟",
            "expected_intent": "invoice_analysis"
        }
    ]

    passed = 0
    failed = 0

    print("\n" + "="*80)
    print("🚀 Running E2E Agentic Workflow Tests (Sprints 1, 2, 3)")
    print("="*80)

    for i, test in enumerate(tests, 1):
        print(f"\nTest {i}/{len(tests)}: {test['name']}")
        print(f"Query: \"{test['query']}\"")
        
        state: M1State = {
            "query": test["query"],
            "language": "auto",
            "intent": "",
            "extracted_params": {},
            "raw_data": [],
            "final_response": {},
            "error": "",
            "needs_clarification": False
        }

        try:
            # LangSmith will trace this entire invocation automatically
            result = await m1_graph.ainvoke(state)
            
            actual_intent = result.get("intent", "")
            narrative = result.get("narrative", "")
            clarification = result.get("clarification_message", "")
            is_clarification = result.get("needs_clarification", False)

            print(f"  ➜ Intent Routed: {actual_intent}")
            
            if is_clarification:
                print(f"  ➜ Agent Response (Clarification): {clarification}")
            else:
                print(f"  ➜ Agent Response (Narrative): {narrative[:200]}...")

            if actual_intent == test["expected_intent"] or is_clarification:
                print(f"  ✅ RESULT: PASS")
                passed += 1
            else:
                print(f"  ❌ RESULT: FAIL (Expected: {test['expected_intent']}, Got: {actual_intent})")
                failed += 1

        except Exception as e:
            print(f"  ❌ RESULT: ERROR - {str(e)}")
            failed += 1

    print("\n" + "="*80)
    print(f"🏁 SUMMARY: {passed} PASSED | {failed} FAILED | {len(tests)} TOTAL")
    print("="*80)

if __name__ == "__main__":
    # Ensure Windows prints utf-8 correctly
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(test_e2e_flow())
