"""Aggregate bounded T3 step results for shared evaluation and rendering."""

from __future__ import annotations

from agents.m1.schemas.m1_state import M1State
from agents.m1.utils.numeric import is_numeric_column, to_float


async def aggregate_results(state: M1State) -> dict:
    failures: list[str] = []
    successful_results = [r for r in state.get("tool_results", []) if r.get("status") == "complete"]
    is_multi_step = len(successful_results) > 1

    # 1. Fetch descriptive step names
    react_plan = state.get("react_plan", [])
    step_legends = {step.get("id"): step.get("legend_label") or step.get("purpose", step.get("id")) for step in react_plan}

    # 2. Aggregate Data
    if is_multi_step:
        pivot_map = {}
        ref_label_col = list(successful_results[0].get("rows")[0].keys())[0] if successful_results and successful_results[0].get("rows") else "period"

        for result in state.get("tool_results", []):
            step_id = result.get("step", {}).get("id", "step")
            
            # fallback labels if LLM missed it
            if step_id == "s1" and step_id not in step_legends: legend = "أوامر البيع"
            elif step_id == "s2" and step_id not in step_legends: legend = "الفواتير"
            else: legend = step_legends.get(step_id, step_id)
            
            if result.get("status") == "complete":
                rows = result.get("rows", [])
                if not rows: continue
                    
                keys = list(rows[0].keys())
                l_col = keys[0]
                # Find first numeric column to be the value — via safe coercion
                # so Decimal and formatted strings ("1,783,555") still count.
                v_col = next(
                    (c for c in keys[1:] if is_numeric_column(rows, c)),
                    keys[-1],
                )

                for row in rows:
                    x_val = row.get(l_col)
                    if x_val is None: continue

                    if x_val not in pivot_map:
                        pivot_map[x_val] = {ref_label_col: x_val}
                    value = row.get(v_col)
                    coerced = to_float(value)
                    pivot_map[x_val][legend] = coerced if coerced is not None else value
                    
            elif result.get("status") not in {"deferred_to_aggregator"}:
                failures.append(f"{step_id}: {result.get('error_category', 'failed')}")

        aggregated = list(pivot_map.values())
        # Chronological/alphabetical sort
        if ref_label_col and aggregated:
            aggregated.sort(key=lambda x: str(x.get(ref_label_col, "")))

    else:
        # Single step: return rows as is
        aggregated = []
        for result in state.get("tool_results", []):
            step_id = result.get("step", {}).get("id", "step")
            if result.get("status") == "complete":
                aggregated.extend(result.get("rows", []))
            elif result.get("status") not in {"deferred_to_aggregator"}:
                failures.append(f"{step_id}: {result.get('error_category', 'failed')}")

    error = ""
    if not aggregated and failures:
        error = "Analytical plan failed: " + "; ".join(failures)

    return {
        "raw_data": aggregated,
        "error": error,
        "extracted_params": {
            **state.get("extracted_params", {}),
            "analysis_failures": failures,
        },
    }

