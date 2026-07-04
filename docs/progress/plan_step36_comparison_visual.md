# Implementation Plan — Step 36: Comparison Intent → Presentation Layer

**Date:** 2026-07-05 · **Branch:** feature/vercel-deployment · **Prereq:** commit 1f50b3b pushed

## Problem

"قارنلي الربع الأول والتاني" renders the SAME monthly line chart as the previous
turn. The comparison happens only in the narrative. Root design flaw: comparison
knowledge exists in the resolver (`followup_mode=compare`), the frame
(`comparison_range`), and db_query_tool (`comparison` flag) — but never reaches
the chart layer, which decides purely from data shape.

Per design discussion with the user: the target is NOT two aggregate bars
(a 5.6% delta renders as two near-equal bars — low information) but an
**aligned overlay**: series per period, x = position within the period, so
level AND shape are comparable at a glance.

## Design

New deterministic step in `chart_config_node` (the presentation authority):

`_build_comparison_overlay(rows, frame, language)` fires ONLY when ALL hold:
1. `analysis_frame.date_range` and `.comparison_range` both have start+end.
2. A time column exists whose values parse as ISO dates.
3. Bucketing rows by range membership yields ≥2 rows in EACH bucket
   (1-row buckets are already handled by the aggregated 2-bar path).

Output: grouped-bar config, series named by period label (Q1-2024 / Q2-2024,
derived from range start month), x labels "شهر 1..n" / "Month 1..n" aligned by
index, values coerced via to_float. output_format forced to bar_chart
(alert path syncs alert_data_format instead).

Fallbacks preserved: no frame ranges → existing heuristics; aggregated 2-row
comparison → existing 2-bar path; overlapping ranges → base bucket wins,
comparison bucket starves → overlay declines, normal path renders.

## Secondary fixes (from self-review + last screenshot)

- `narrative_generator` prompts: numbers in narratives MUST use thousands
  separators (screenshot showed raw floats `1193770.6` inside parentheses).
- Frontend polish: BarChart value-axis name was computed but never wired
  (unused `yAxisLabel`); LineChart axis-name styling too faint (10px #64748B).

## Explicitly NOT in this round

- json_schema structured-output migration (queued next, see Step 35).
- MetricCard `day|year` token over-matching (documented; real impact ~0).
- Lexical sort of non-quarter period labels ("M10" < "M5") — rare edge.

## Verification

- Scratchpad suite: overlay case (6 monthly rows + Q1/Q2 frame → 2 series ×
  3 points, correct names/labels), regression: same rows WITHOUT frame ranges
  still render monthly line; aggregated 2-row path unchanged. All prior tests.
- `python -c` graph builds; `npm run build`.
- Log as Step 36; commit + push.
