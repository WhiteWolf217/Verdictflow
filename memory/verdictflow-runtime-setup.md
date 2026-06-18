---
name: verdictflow-runtime-setup
description: How to run VerdictFlow locally and its non-obvious runtime facts (Gemini LLM, in-memory Qdrant, Band fallback)
metadata:
  type: project
---

VerdictFlow = multi-agent contract-review app. Backend = FastAPI (Python 3.10 venv at `backend/.venv`), frontend = Next.js 14 (`frontend/`).

Non-obvious runtime facts (differ from README/docs):
- **LLM is Google Gemini**, not Anthropic/OpenAI/Featherless as the README/architecture.md claim. All agents call `core/llm.py:llm_generate()` → `google-genai` (`from google import genai`), `DEFAULT_MODEL = "gemini-2.5-flash"`, key = `GEMINI_API_KEY` in `backend/.env`.
- `google-genai` was **missing from `backend/pyproject.toml`** (only anthropic/openai listed); I installed it into the venv and added it to pyproject. If recreating the venv, `pip install -e .` now pulls it.
- **Qdrant runs in-memory** (`QDRANT_URL=:memory:` in `.env`) — no Docker needed. FastEmbed downloads MiniLM (~90MB) on first run.
- **Band SDK is not installed**; `BandClientWrapper` runs in `band_rest` mode but the API key returns 401. This is **non-fatal** — every Band HTTP call is try/except wrapped and mirrors to an in-memory transcript, so the pipeline always continues.

Run commands:
- Backend: from `backend/`, `.venv/Scripts/python.exe -m uvicorn main:app --port 8000` (health: `GET /health`, 17 routes under `/api`).
- Frontend: from `frontend/`, `npm run dev` (serves :3000, `.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000/api`).
- Deterministic smoke test (no LLM): `backend/.venv/Scripts/python.exe tests/smoke_phases.py`.

**LLM throughput tuning (critical for demos)** — Gemini free tier is per-MINUTE capped: gemini-2.5-flash = 5 RPM, gemini-2.5-flash-lite = 15 RPM, gemini-2.0-flash/-lite = 0 free quota on this project. A full pipeline fires ~8 LLM calls/contract after optimization (was ~19). Config in `.env`: `GEMINI_MODEL=gemini-2.5-flash-lite`, `GEMINI_RPM=14`. `core/llm.py` has a global sliding-window rate limiter (`GEMINI_RPM`/min), empty-response retry, and `parse_json_response` salvages truncated JSON arrays. Clause analyst batches all 12 categories into ONE call. Red Team attacker needs `max_tokens>=8192` (verbose output truncates at 3000). With these, a full run = ~40s and all 6 agents produce rich results (e.g. Clause 14, RedTeam 8, Financial 11, Compliance 6, Redline 13). Daily quota is per-PROJECT (shared across keys with same prefix); enable billing + set `GEMINI_MODEL=gemini-2.5-flash` + high `GEMINI_RPM` for best quality/speed. See [[verdictflow-frontend-api-fixes]] and [[verdictflow-band-agents]].
