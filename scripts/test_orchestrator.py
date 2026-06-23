import asyncio
import uuid
from backend.api.v1.m1_query import QueryRequest, handle_query
from backend.core.auth import UserContext

async def interactive_chat():
    print("========================================")
    print("🤖 Wakeel Orchestrator - Interactive Chat")
    print("Type 'exit' or 'quit' to stop.")
    print("========================================")
    
    # We create a persistent user and session_id to maintain chat history
    user = UserContext(user_id=str(uuid.uuid4()), email="test@example.com", role="admin", permissions=[])
    session_id = str(uuid.uuid4())
    
    while True:
        try:
            query = input("\n👤 You: ")
            if query.lower() in ["exit", "quit", "خروج"]:
                print("👋 Goodbye!")
                break
            
            if not query.strip():
                continue
                
            req = QueryRequest(query=query, language="auto", session_id=session_id)
            print("⏳ Thinking...")
            
            resp = await handle_query(req, user)
            
            print(f"🤖 Wakeel: {resp.narrative}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(interactive_chat())
