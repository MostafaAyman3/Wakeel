"""Load structured analytical context from recent conversation metadata."""

from __future__ import annotations

from agents.m1.schemas.m1_state import M1State


async def load_context(state: M1State) -> dict:
    history = state.get("chat_history", [])
    metadata_entries: list[dict] = []
    prior_analysis_frame: dict = {}
    prior_result_summary: dict = {}
    clarification: dict = {}

    for turn in history:
        metadata = turn.get("metadata")
        if not isinstance(metadata, dict) or not metadata:
            continue
        metadata_entries.append(metadata)
        if turn.get("role") == "assistant":
            frame = metadata.get("analysis_frame")
            if isinstance(frame, dict) and frame:
                prior_analysis_frame = frame
            summary = metadata.get("result_summary")
            if isinstance(summary, dict) and summary:
                prior_result_summary = summary
            pending = metadata.get("clarification")
            if isinstance(pending, dict) and pending.get("pending"):
                clarification = pending
            else:
                # A newer assistant turn without a pending clarification clears
                # any older pending state from the same history window.
                clarification = {}

    return {
        "conversation_metadata": metadata_entries,
        "prior_analysis_frame": prior_analysis_frame,
        "prior_result_summary": prior_result_summary,
        "clarification_pending": bool(clarification),
        "clarification_original_query": clarification.get("original_query", ""),
        "clarification_missing_slots": clarification.get("missing_slots", []),
    }
