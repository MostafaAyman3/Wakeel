# M3 Sprint 5 — Execution Log (Frontend + MVP wiring)

> Dedicated record for **M3 Sprint 5**: Customer Input Interface + Human Review
> Interface, wired end-to-end into a demo-able MVP.
> Date: 2026-06-22 · Branch: `m3-sprint4-human-review-escalation`

---

## Goal

Build the two M3 frontends (customer input + agent review) and connect them to
the live backend so the full human-in-the-loop flow can be demoed.

## What was built

### Backend
- **`backend/api/v1/auth.py`** — `POST /api/v1/auth/login`. MVP demo auth: any
  email + shared password `demo1234` → JWT (role embedded). Wired into
  `backend/main.py`. Needed because `/support` requires a Bearer token.
- **`backend/services/human_review_service.py`** — made audit logging
  **best-effort** (`_safe_log`) so a transient audit-DB hiccup never turns an
  approve/reject/escalate into an HTTP 500 (matches the escalation_node pattern).

### Frontend (Next.js 14 / React 18 / Tailwind)
- Infra: `next.config.mjs`, `postcss.config.mjs`, `app/globals.css`,
  `app/layout.tsx` (imports globals), `tsconfig.json` (`@/*` path alias).
- `lib/api.ts` — fetch client: base URL, JWT in localStorage, **auto demo
  login**, 401-retry, and the M3 endpoints (submit / approve / reject / escalate).
- `types/m3.ts` — types mirroring the backend contract.
- `hooks/useM3Support.ts` — submit + approve + reject(&regenerate) + escalate;
  remembers the last request so Reject & Regenerate replays it with
  `rejection_context`.
- Components (`components/m3/`):
  - `ConfidenceIndicator` — 🟢/🟡/🔴 badge (agent-only).
  - `TransparencyPanel` — invoice / order / shipping / history the agent used.
  - `CustomerInputForm` — identifier (optional) + issue text + demo quick-fill.
  - `HumanReviewPanel` — editable draft + transparency + confidence + 3 actions.
  - `EscalationView` — escalated-case summary for the supervisor.
- `app/m3/page.tsx` — tabbed Customer / Agent Review on one screen; `app/page.tsx`
  redirects to `/m3`.

## Verification
- `npm install` (147 pkgs) + `npm run build` → **compiled successfully**, type
  check passed, `/m3` route built.
- Backend test suites still green: `test_m3_sprint1` 5/5, `test_m3_sprint4` 12/12.
- E2E HTTP flow (TestClient): login → `/support` (billing_dispute → review
  required, High confidence) → approve / reject / escalate all return 200.
- Live invoice fetch confirmed: response addresses the real customer name
  ("Omar Tarek"), transparency panel shows invoice + history.

## How to run the demo
```bash
# Terminal 1 — backend
pip install -r backend/requirements.txt          # once
uvicorn backend.main:app --reload                 # http://localhost:8000

# Terminal 2 — frontend
cd frontend
npm install                                       # once
npm run dev                                        # http://localhost:3000  → redirects to /m3
```
Open http://localhost:3000 . The page auto-logs-in with the demo user. Use the
quick-fill chips (ORD-2024-1567 / INV-0001 / CUST-001 / DEL-999) to exercise the
four demo scenarios.

## Notes / follow-ups
- Demo auth is intentionally minimal (shared password) — replace with a real
  user store + hashing post-MVP.
- On Windows, harmless `Event loop is closed` SSL noise appears at process
  teardown (asyncpg + ProactorEventLoop); not an app fault.
- Remaining: **Sprint 6** — integration polish + the 4 demo scenarios scripted
  end-to-end, and (optional) a dedicated supervisor escalation queue view.
