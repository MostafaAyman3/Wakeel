"""
Fetch and analyze a LangSmith trace for debugging M1 agent issues.

Usage: python scripts/debug_langsmith_trace.py <run_id>
"""

import os
import sys
import json
from datetime import datetime

# Load .env
from dotenv import load_dotenv
load_dotenv()

from langsmith import Client

def format_duration(start, end):
    if start and end:
        delta = end - start
        return f"{delta.total_seconds():.2f}s"
    return "N/A"

def truncate(text, max_len=500):
    if not text:
        return "(empty)"
    s = str(text)
    return s[:max_len] + "..." if len(s) > max_len else s

def main():
    run_id = sys.argv[1] if len(sys.argv) > 1 else "34afbba8-464b-4c2b-84d0-e20210a59728"
    
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("ERROR: LANGCHAIN_API_KEY not found in .env")
        sys.exit(1)
    
    client = Client(api_key=api_key)
    
    print(f"\n{'='*80}")
    print(f"  LangSmith Trace Analysis — Thread ID: {run_id}")
    print(f"{'='*80}\n")
    
    # ── 1. Search for runs matching this thread/session ID ─────────
    # The ID could be a run_id, session_id in metadata, or a tag.
    # Try multiple strategies.
    
    project_name = os.getenv("LANGCHAIN_PROJECT", "Wakeel")
    root_run = None
    all_root_runs = []
    
    # Strategy 1: Try direct run_id fetch
    try:
        root_run = client.read_run(run_id)
        print(f"  Found by run_id directly.\n")
        all_root_runs = [root_run]
    except Exception:
        pass
    
    # Strategy 2: Search by metadata session_id
    if not root_run:
        try:
            runs = list(client.list_runs(
                project_name=project_name,
                filter=f'has(metadata, {{"session_id": "{run_id}"}})',
                limit=20,
            ))
            if runs:
                runs.sort(key=lambda r: r.start_time or datetime.min)
                all_root_runs = runs
                root_run = runs[-1]  # most recent
                print(f"  Found {len(runs)} run(s) by metadata session_id.\n")
        except Exception as e:
            print(f"  Strategy 2 error: {e}")
    
    # Strategy 3: Search by tag
    if not root_run:
        try:
            runs = list(client.list_runs(
                project_name=project_name,
                filter=f'has(tags, "{run_id}")',
                limit=20,
            ))
            if runs:
                runs.sort(key=lambda r: r.start_time or datetime.min)
                all_root_runs = runs
                root_run = runs[-1]
                print(f"  Found {len(runs)} run(s) by tag.\n")
        except Exception as e:
            print(f"  Strategy 3 error: {e}")
    
    # Strategy 4: List recent runs and search
    if not root_run:
        try:
            runs = list(client.list_runs(
                project_name=project_name,
                filter='eq(name, "wakeel-m1-query")',
                limit=30,
            ))
            matching = []
            for r in runs:
                meta = r.metadata or {}
                if meta.get("session_id") == run_id:
                    matching.append(r)
                elif r.inputs:
                    if r.inputs.get("session_id") == run_id:
                        matching.append(r)
            if matching:
                matching.sort(key=lambda r: r.start_time or datetime.min)
                all_root_runs = matching
                root_run = matching[-1]
                print(f"  Found {len(matching)} run(s) by scanning recent runs.\n")
        except Exception as e:
            print(f"  Strategy 4 error: {e}")
    
    if not root_run:
        print(f"ERROR: Could not find any runs for ID: {run_id}")
        print(f"  Listing last 10 runs in project '{project_name}':")
        try:
            recent = list(client.list_runs(project_name=project_name, limit=10))
            for r in recent:
                meta = r.metadata or {}
                print(f"    {r.id} | {r.name} | {r.status} | session={meta.get('session_id', 'N/A')} | {r.start_time}")
        except Exception as e2:
            print(f"    List error: {e2}")
 
    # ── Process ALL runs in this session ───────────────────────────
    for run_idx, root_run in enumerate(all_root_runs, 1):
        print(f"\n{'#'*80}")
        print(f"  RUN {run_idx}/{len(all_root_runs)} — {root_run.id}")
        print(f"{'#'*80}")
        
        print(f"\n  Name:       {root_run.name}")
        print(f"  Status:     {root_run.status}")
        print(f"  Run Type:   {root_run.run_type}")
        print(f"  Duration:   {format_duration(root_run.start_time, root_run.end_time)}")
        print(f"  Start:      {root_run.start_time}")
        print(f"  Tags:       {root_run.tags}")
        print(f"  Metadata:   {json.dumps(root_run.metadata or {}, ensure_ascii=False, indent=2)}")
        
        # Print root inputs
        print(f"\n  === INPUTS ===")
        if root_run.inputs:
            for key, val in root_run.inputs.items():
                print(f"    {key}: {truncate(val, 300)}")
        
        # Print root outputs
        print(f"\n  === OUTPUTS ===")
        if root_run.outputs:
            for key, val in root_run.outputs.items():
                print(f"    {key}: {truncate(val, 300)}")
        
        if root_run.error:
            print(f"\n  === ERROR ===")
            print(f"    {root_run.error}")
        
        # ── Fetch child runs for THIS specific root run ───────────
        print(f"\n  {'─'*70}")
        print(f"  CHILD RUNS (Pipeline Steps)")
        print(f"  {'─'*70}")
        
        children = list(client.list_runs(
            project_name=project_name,
            filter=f'eq(parent_run_id, "{root_run.id}")',
        ))
        
        children.sort(key=lambda r: r.start_time or datetime.min)
        
        for i, child in enumerate(children, 1):
            duration = format_duration(child.start_time, child.end_time)
            status_icon = "✅" if child.status == "success" else "❌" if child.status == "error" else "⏳"
            
            print(f"\n  [{i}] {status_icon} {child.name}")
            print(f"      Type:     {child.run_type}")
            print(f"      Duration: {duration}")
            print(f"      Status:   {child.status}")
            
            if child.inputs:
                print(f"      Inputs:")
                for key, val in child.inputs.items():
                    print(f"        {key}: {truncate(val, 200)}")
            
            if child.outputs:
                print(f"      Outputs:")
                for key, val in child.outputs.items():
                    print(f"        {key}: {truncate(val, 200)}")
            
            if child.error:
                print(f"      ERROR: {child.error}")
            
            # Fetch grandchildren (LLM calls)
            grandchildren = list(client.list_runs(
                project_name=project_name,
                filter=f'eq(parent_run_id, "{child.id}")',
            ))
            grandchildren.sort(key=lambda r: r.start_time or datetime.min)
            
            for j, gc in enumerate(grandchildren, 1):
                gc_duration = format_duration(gc.start_time, gc.end_time)
                gc_icon = "✅" if gc.status == "success" else "❌"
                
                print(f"\n      [{i}.{j}] {gc_icon} {gc.name} ({gc.run_type}) — {gc_duration}")
                
                if gc.run_type == "llm" and gc.inputs:
                    messages = gc.inputs.get("messages", [])
                    if messages:
                        print(f"            Messages ({len(messages)} total):")
                        for msg in messages:
                            if isinstance(msg, dict):
                                role = msg.get("type", msg.get("role", "?"))
                                content = msg.get("content", "")
                                if not content and isinstance(msg.get("data"), dict):
                                    content = msg["data"].get("content", "")
                            elif isinstance(msg, list) and len(msg) >= 2:
                                role = msg[0]
                                content = msg[1] if isinstance(msg[1], str) else str(msg[1])
                            else:
                                role = "?"
                                content = str(msg)
                            print(f"              [{role}]: {truncate(content, 150)}")
                    
                    if gc.outputs:
                        generations = gc.outputs.get("generations", [])
                        if generations:
                            for gen_list in generations:
                                if isinstance(gen_list, list):
                                    for gen in gen_list:
                                        text = gen.get("text", "") or gen.get("message", {}).get("content", "")
                                        print(f"            LLM Output: {truncate(text, 300)}")
                                elif isinstance(gen_list, dict):
                                    text = gen_list.get("text", "") or gen_list.get("message", {}).get("content", "")
                                    print(f"            LLM Output: {truncate(text, 300)}")
                
                elif gc.outputs:
                    for key, val in gc.outputs.items():
                        print(f"            {key}: {truncate(val, 150)}")
                
                if gc.error:
                    print(f"            ERROR: {gc.error}")
        
        # ── Analysis for this run ─────────────────────────────────
        print(f"\n  {'─'*70}")
        print(f"  ANALYSIS for Run {run_idx}")
        print(f"  {'─'*70}")
        
        root_inputs = root_run.inputs or {}
        chat_history = root_inputs.get("chat_history", [])
        session_id_val = root_inputs.get("session_id", "")
        query = root_inputs.get("query", "")
        
        print(f"  query:              {truncate(query, 200)}")
        print(f"  session_id present: {'✅ ' + str(session_id_val) if session_id_val else '❌ MISSING'}")
        print(f"  chat_history len:   {len(chat_history) if isinstance(chat_history, list) else '❌ NOT A LIST'}")
        
        if isinstance(chat_history, list) and chat_history:
            print(f"  chat_history:")
            for idx, msg in enumerate(chat_history):
                if isinstance(msg, dict):
                    print(f"    [{idx}] {msg.get('role', '?')}: {truncate(msg.get('content', ''), 150)}")
        
        for child in children:
            if "intent" in (child.name or "").lower() or "classify" in (child.name or "").lower():
                if child.outputs:
                    for key, val in child.outputs.items():
                        if isinstance(val, dict):
                            print(f"  Intent:   {val.get('intent', 'N/A')}")
                            print(f"  Params:   {json.dumps(val.get('extracted_params', {}), ensure_ascii=False, default=str)}")
                            break
        
        root_outputs = root_run.outputs or {}
        final_resp = root_outputs.get("final_response", {})
        if isinstance(final_resp, dict):
            print(f"  Format:   {final_resp.get('format', 'N/A')}")
            print(f"  Narrative: {truncate(final_resp.get('narrative', ''), 200)}")
    
    print(f"\n{'='*80}")
    print(f"  END OF ANALYSIS")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
