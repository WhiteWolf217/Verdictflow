---
name: verdictflow-frontend-api-fixes
description: Frontend build was broken on main — missing lib/api.ts exports and CaseDetail fields; what I added
metadata:
  type: project
---

On `main`, `frontend` did not compile (`next build` failed). Root causes and fixes in `frontend/lib/api.ts`:
- `CaseDetail` type was missing `verdict`, `verdict_recommendation`, `confidence_score`, `band_room_id` — the backend `GET /api/cases/{id}` returns them (`api/routes.py:149-151`), and `app/cases/[id]/page.tsx` reads `caseData.verdict` etc. (fatal type error).
- `components/negotiate-tab.tsx` imported 4 functions that didn't exist: `getNegotiationCoaching`, `startSimulation`, `sendSimulationTurn`, `evaluateNegotiation`, plus types `NegotiationStrategy`/`NegotiationEvaluation`. I added them, targeting `POST /api/negotiate/{coach,start,turn,evaluate}` (router in `backend/api/negotiate.py`, mounted so paths are literally `/api/negotiate/...` and align with `API_BASE` = `.../api`).
- `page.tsx` dynamically imports `downloadAudit` → added it (fetches `GET /api/cases/{id}/download` blob, triggers browser .docx download).

After these, `npm run build` succeeds (only a non-blocking react-hooks/exhaustive-deps warning in `agent-progress.tsx`). Related: [[verdictflow-runtime-setup]].
