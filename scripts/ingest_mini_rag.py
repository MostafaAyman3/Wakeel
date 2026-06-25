"""
Ingest knowledge-base documents into the Mini-RAG service (T003).

For each collection it runs Mini-RAG's pipeline:
    upload (per file) -> process (chunk, do_reset) -> push (embed+index) -> info

Collections:
    project_id=1  support_kb  -> data/support_kb/*.txt
    project_id=2  tax         -> data/tax_knowledge_base/processed/*.txt

Prerequisites:
    - Supabase migration applied with vector(1536) column.
    - Mini-RAG running (default http://localhost:8001) with OpenAI + 1536 config.

Usage:
    python scripts/ingest_mini_rag.py                 # both collections
    python scripts/ingest_mini_rag.py --only support  # support_kb only
    python scripts/ingest_mini_rag.py --only tax       # tax only
    python scripts/ingest_mini_rag.py --base-url http://localhost:8001
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import httpx

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

COLLECTIONS = {
    "support": {"project_id": 1, "glob": os.path.join(_ROOT, "data", "support_kb", "*.txt")},
    "tax": {"project_id": 2, "glob": os.path.join(_ROOT, "data", "tax_knowledge_base", "processed", "*.txt")},
}

PASS = "[OK]"
FAIL = "[FAIL]"


def ingest_collection(base_url: str, name: str, project_id: int, pattern: str) -> bool:
    files = sorted(glob.glob(pattern))
    print(f"\n=== Collection '{name}' (project_id={project_id}) ===")
    if not files:
        print(f"  {FAIL} no files matched {pattern}")
        return False
    print(f"  Found {len(files)} file(s).")

    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        # 1) Upload each file
        for fp in files:
            fname = os.path.basename(fp)
            with open(fp, "rb") as fh:
                resp = client.post(
                    f"/api/v1/data/upload/{project_id}",
                    files={"file": (fname, fh, "text/plain")},
                )
            if resp.status_code != 200:
                print(f"  {FAIL} upload {fname}: {resp.status_code} {resp.text[:200]}")
                return False
            print(f"  uploaded: {fname}  -> file_id={resp.json().get('file_id')}")

        # 2) Process all files in the project (reset chunks first)
        resp = client.post(
            f"/api/v1/data/process/{project_id}",
            json={"chunk_size": 1024, "overlap_size": 80, "do_reset": 1},
        )
        if resp.status_code != 200:
            print(f"  {FAIL} process: {resp.status_code} {resp.text[:300]}")
            return False
        pdata = resp.json()
        print(f"  processed: {pdata.get('processed_files')} file(s), "
              f"{pdata.get('inserted_chunks')} chunk(s)")

        # 3) Push: embed + index into the vector DB (reset vectors first)
        resp = client.post(
            f"/api/v1/nlp/index/push/{project_id}",
            json={"do_reset": 1},
        )
        if resp.status_code != 200:
            print(f"  {FAIL} push: {resp.status_code} {resp.text[:300]}")
            return False
        print(f"  indexed: {resp.json().get('inserted_items_count')} vector(s)")

        # 4) Verify
        resp = client.get(f"/api/v1/nlp/index/info/{project_id}")
        if resp.status_code != 200:
            print(f"  {FAIL} info: {resp.status_code} {resp.text[:200]}")
            return False
        info = resp.json().get("collection_info") or {}
        count = info.get("record_count")
        ok = bool(count and count > 0)
        print(f"  {PASS if ok else FAIL} index/info record_count = {count}")
        return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest KB docs into Mini-RAG")
    parser.add_argument("--base-url", default=os.environ.get("MINI_RAG_BASE_URL", "http://localhost:8001"))
    parser.add_argument("--only", choices=["support", "tax"], help="Ingest one collection only")
    args = parser.parse_args()

    targets = [args.only] if args.only else ["support", "tax"]
    print(f"Mini-RAG base URL: {args.base_url}")

    # Quick reachability check
    try:
        httpx.get(f"{args.base_url}/docs", timeout=5)
    except Exception as exc:
        print(f"\n{FAIL} Cannot reach Mini-RAG at {args.base_url}: {exc}")
        print("  Start it first:  cd MIni-RAG-APP-V1/src ; uvicorn main:app --port 8001")
        sys.exit(1)

    results = {}
    for t in targets:
        c = COLLECTIONS[t]
        results[t] = ingest_collection(args.base_url, t, c["project_id"], c["glob"])

    print("\n" + "=" * 50)
    all_ok = all(results.values())
    for t, ok in results.items():
        print(f"  {PASS if ok else FAIL}  {t}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
