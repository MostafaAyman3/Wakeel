import sys
sys.path.insert(0, "D:/Wakeel")

errors = []

checks = [
    ("config",        "from backend.core.config import get_settings; s=get_settings(); print(f'  app={s.app_name} env={s.app_env}')"),
    ("logging",       "from backend.core.logging import configure_logging, get_logger; configure_logging()"),
    ("database",      "from backend.core.database import engine, readonly_engine; print(f'  host={engine.url.host}')"),
    ("auth",          "from backend.core.auth import create_access_token, verify_token; t=create_access_token('u1','x@x.com'); p=verify_token(t); print(f'  JWT OK sub={p.sub}')"),
    ("error_handler", "from backend.middleware.error_handler import error_handler_middleware; print('  middleware OK')"),
    ("llm_shared",    "from agents.shared.llm_client import llm_primary, llm_fast, embeddings; print(f'  primary={llm_primary.model_name} fast={llm_fast.model_name}')"),
    ("llm_backend",   "from backend.services.llm_client import llm_primary, llm_fast; print('  re-export OK')"),
    ("routers",       "from backend.api.v1.m1_query import router as r1; from backend.api.v1.m3_support import router as r3; print(f'  M1={r1.prefix} M3={r3.prefix}')"),
    ("main_app",      "from backend.main import app; routes=[r.path for r in app.routes]; print(f'  routes count={len(routes)}')"),
]

for name, code in checks:
    try:
        exec(code)
        print(f"[PASS] {name}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        errors.append(name)

print()
if errors:
    print("FAILED:", errors)
    sys.exit(1)
else:
    print("ALL 9 CHECKS PASSED — Sprint 0 infrastructure complete")
