---
name: verdictflow-band-agents
description: How VerdictFlow's 6 Band agents are wired, the per-agent-chat constraint, and the key/auth facts
metadata:
  type: project
---

VerdictFlow coordinates 6 Band.ai agents. Verified facts (tested live against the API):

**Auth**: Band REST Agent API base = `https://app.band.ai/api/v1`, auth header = `X-API-Key: <agent_key>` (NOT Bearer). `GET /agent/me` returns `{"data": {handle, id, name}}`.

**The 6 agents** (handle `@thearpit2005/vf-*`), keys in `backend/.env` as `BAND_<ROLE>_KEY`, ids as `BAND_<ROLE>_ID`: intake, clause, redteam (red-team), compliance, financial, redline. All 6 keys validated 200.

**Dead key gotcha**: the old `BAND_API_KEY` (`band_a_1781725757_...`) was invalid ("API key not linked to a user or agent"). There is no dedicated orchestrator agent, so `BAND_API_KEY`/`BAND_AGENT_ID` now point at the **intake** agent as the lead/coordinator identity.

**Critical constraint — Agent API chats are per-agent**: an agent's key can ONLY see/post to chats IT created. Posting to another agent's chat → 404. You cannot add another agent to your chat via the Agent API (`mentioned_participant_not_in_room`; needs the Human/Workspace API we don't have). So a single shared "case room" across agents is impossible here.
- `POST /agent/chats` (body `{"chat":{"title":...}}`) → creates a chat, returns `data.id`.
- `POST /agent/chats/{id}/events` (body `{"event":{"content","message_type":"thought","metadata":{}}}`) → works (201). This is the channel agents use to log findings/thoughts.
- `POST /agent/chats/{id}/messages` requires `{"message":{"content","mentions":[{"id":<other-agent-id>}]}}` with a NON-self mention → not usable for solo posting (`cannot_mention_self`).

**Implementation** (`backend/band/client.py`, rewritten): each agent lazily creates its OWN Band chat on first message and posts events to it with its own key; `agents/orchestrator.py` posts once per agent (Intake, Clause Analyst, Red Team, Financial Risk, Compliance, Redline) so all 6 are genuinely active. A unified in-memory transcript (`_rooms`) mirrors everything for the UI (`/api/cases/{id}/room`) and audit. Orchestrator/Adjudicator have no Band identity → in-memory only.

**Verify it**: `PYTHONUTF8=1 backend/.venv/Scripts/python.exe tests/band_integration.py` → "All 6 agents are live on Band". Startup log shows "✅ All 6 Band agents verified and ready". See [[verdictflow-runtime-setup]].
