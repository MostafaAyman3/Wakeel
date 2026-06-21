"""Quick test: send a query and verify LangSmith tracing is active."""
import json
import urllib.request
import urllib.error
import sys
sys.path.insert(0, ".")

from jose import jwt
from datetime import datetime, timedelta, timezone

SECRET = "8414421fdbaad8c9f3786d3aa4228a8a6f68c8d94840401103fea9399bd48993"

token = jwt.encode(
    {
        "sub": "test-user",
        "email": "test@wakeel.ai",
        "role": "admin",
        "permissions": ["read"],
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
    },
    SECRET,
    algorithm="HS256",
)

req = urllib.request.Request(
    "http://localhost:8000/api/v1/query",
    data=json.dumps({"query": "What is total revenue?", "language": "en"}).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    },
)

try:
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read())
    print("✅ SUCCESS")
    print(f"  Format: {data.get('format')}")
    print(f"  Narrative: {(data.get('narrative') or '')[:200]}")
    print("\n→ Check LangSmith at https://smith.langchain.com — project 'Wakeel'")
except urllib.error.HTTPError as e:
    print(f"❌ HTTP {e.code}: {e.reason}")
    print(e.read().decode()[:500])
except Exception as e:
    print(f"❌ Error: {e}")
