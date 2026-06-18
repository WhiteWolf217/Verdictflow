"""
VerdictFlow — Band REST API Client

Connects to Band.ai via their REST Agent API (https://app.band.ai/api/v1).
No SDK dependency — uses httpx for HTTP calls.

── Why per-agent chats? ──────────────────────────────────────────────────────
The Band Agent API scopes every chat to the agent that created it: an agent's
API key can only see and post to its OWN chats. Posting to another agent's chat
returns 404. This was verified empirically (tests/band_flow_probe.py).

Therefore a single shared "case room" cannot carry messages from all 6 agents.
Instead, each agent gets its OWN Band chat (created lazily with that agent's
key the first time it speaks). The unified, cross-agent transcript that the UI
and audit packet consume is kept in-memory and mirrors every message/event.

Key endpoints used:
- GET  /agent/me                     → verify agent identity
- POST /agent/chats                  → create a chat (per agent)
- POST /agent/chats/{id}/events      → post a message/event to that agent's chat
- GET  /agent/chats/{id}/messages    → read an agent's chat history
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger("verdictflow.band")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Canonical agent name → (env key var, env id var). Names are matched
# case-insensitively, so the orchestrator may pass "Intake Agent", "intake",
# etc. Roles NOT in this map (Orchestrator, Adjudicator) have no Band identity
# and are mirrored in-memory only.
_AGENT_ENV = {
    "intake agent":   ("BAND_INTAKE_KEY", "BAND_INTAKE_ID"),
    "clause analyst": ("BAND_CLAUSE_KEY", "BAND_CLAUSE_ID"),
    "red team":       ("BAND_REDTEAM_KEY", "BAND_REDTEAM_ID"),
    "compliance":     ("BAND_COMPLIANCE_KEY", "BAND_COMPLIANCE_ID"),
    "financial risk": ("BAND_FINANCIAL_KEY", "BAND_FINANCIAL_ID"),
    "redline":        ("BAND_REDLINE_KEY", "BAND_REDLINE_ID"),
}

# Tolerant aliases → canonical name.
_AGENT_ALIASES = {
    "intake": "intake agent",
    "intake agent": "intake agent",
    "clause": "clause analyst",
    "clause analyst": "clause analyst",
    "red team": "red team",
    "redteam": "red team",
    "red_team": "red team",
    "compliance": "compliance",
    "compliance agent": "compliance",
    "financial": "financial risk",
    "financial risk": "financial risk",
    "financial_risk": "financial risk",
    "redline": "redline",
    "redline agent": "redline",
}


def _canonical(agent_name: str) -> Optional[str]:
    return _AGENT_ALIASES.get(agent_name.strip().lower())


class BandClientWrapper:
    """
    Direct REST integration with the Band.ai Agent API.

    Each VerdictFlow agent posts to its own Band chat (Agent API chats are
    per-agent). A unified in-memory transcript mirrors all agents for the UI
    and audit packet. Every network call is best-effort: failures are logged
    and the in-memory mirror always stays authoritative for the UI.
    """

    def __init__(self):
        # Lead/coordinator identity (Intake doubles as platform identity since
        # there is no dedicated orchestrator agent).
        self.api_key = os.getenv("BAND_API_KEY", "")
        self.agent_id = os.getenv("BAND_AGENT_ID", "")

        # Per-agent credentials, resolved from env.
        self.agent_keys: dict[str, str] = {}
        self.agent_ids: dict[str, str] = {}
        for canon, (key_var, id_var) in _AGENT_ENV.items():
            key = os.getenv(key_var, "")
            if key:
                self.agent_keys[canon] = key
                self.agent_ids[canon] = os.getenv(id_var, "")

        self.rest_url = os.getenv("BAND_REST_URL", "https://app.band.ai").rstrip("/")
        self.base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

        self._available = False
        self._http: Optional[httpx.AsyncClient] = None

        # In-memory transcript mirror: room_id → {name, case_id, messages, events}
        self._rooms: dict[str, dict] = {}
        # Per-agent Band chats: room_id → {canonical_agent_name → band_chat_id}
        self._agent_chats: dict[str, dict[str, str]] = {}

        if self.api_key and self.agent_keys:
            self._http = httpx.AsyncClient(
                base_url=f"{self.rest_url}/api/v1",
                headers={"Content-Type": "application/json"},
                timeout=15.0,
            )
            self._available = True
            logger.info(
                f"✅ Band REST client initialised — lead agent={self.agent_id[:8]}..., "
                f"{len(self.agent_keys)} agent identities loaded"
            )
        else:
            logger.info(
                "ℹ️  BAND_API_KEY or agent keys not set — using in-memory case rooms (demo mode)."
            )

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def mode(self) -> str:
        return "band_rest" if self._available else "in_memory"

    # ── In-memory transcript helpers ─────────────────────────────────────────

    def room_url(self, room_id: Optional[str]) -> Optional[str]:
        if not room_id:
            return None
        return f"{self.base_url}/api/rooms/{room_id}"

    def get_transcript(self, room_id: str) -> Optional[dict]:
        room = self._rooms.get(room_id)
        if not room:
            return None
        return {
            "room_id": room_id,
            "url": self.room_url(room_id),
            "mode": self.mode,
            "agent_chats": self._agent_chats.get(room_id, {}),
            **room,
        }

    def _record_message(self, room_id: str, agent_name: str, message: str) -> None:
        room = self._rooms.setdefault(
            room_id, {"name": room_id, "case_id": None, "messages": [], "events": [], "created_at": _now()}
        )
        room["messages"].append({"agent": agent_name, "message": message, "timestamp": _now()})

    def _record_event(self, room_id: str, event_type: str, payload: dict) -> None:
        room = self._rooms.setdefault(
            room_id, {"name": room_id, "case_id": None, "messages": [], "events": [], "created_at": _now()}
        )
        room["events"].append({"event_type": event_type, "payload": payload, "timestamp": _now()})

    # ── Band REST API: Verify Identity ───────────────────────────────────────

    async def verify_identity(self, api_key: Optional[str] = None) -> Optional[dict]:
        """Verify an agent is properly connected to Band. Defaults to the lead key."""
        if not self._available or not self._http:
            return None
        key = api_key or self.api_key
        try:
            resp = await self._http.get("/agent/me", headers={"X-API-Key": key})
            resp.raise_for_status()
            raw = resp.json()
            data = raw.get("data", raw)  # Band wraps in {"data": {...}}
            return data
        except Exception as e:
            logger.warning(f"⚠️  Band identity verification failed: {e}")
            return None

    async def verify_all_agents(self) -> dict[str, bool]:
        """Verify every configured agent key. Returns {canonical_name: ok}."""
        results: dict[str, bool] = {}
        for canon, key in self.agent_keys.items():
            identity = await self.verify_identity(key)
            ok = bool(identity)
            results[canon] = ok
            if ok:
                logger.info(f"   ✅ {canon:15} → {identity.get('handle') or identity.get('name')}")
            else:
                logger.warning(f"   ❌ {canon:15} → key rejected")
        return results

    # ── Band REST API: Create Case Room (in-memory; chats are per-agent) ─────

    async def create_case_room(self, case_id: str, contract_name: str) -> Optional[str]:
        """
        Open a case room. The unified room is in-memory; per-agent Band chats
        are created lazily as each agent first speaks. Returns the room_id.
        """
        room_id = f"case_{case_id[:8]}"
        self._rooms[room_id] = {
            "name": f"VerdictFlow Case: {contract_name}",
            "case_id": case_id,
            "messages": [],
            "events": [],
            "created_at": _now(),
        }
        self._agent_chats.setdefault(room_id, {})
        self._record_message(
            room_id, "System",
            f"📋 Case room opened for '{contract_name}'. Agents assembling...",
        )
        logger.info(f"🏠 Case room '{room_id}' ready ({self.mode}) for case '{case_id}'")
        return room_id

    # ── Per-agent chat creation (lazy) ───────────────────────────────────────

    async def _ensure_agent_chat(self, room_id: str, agent_name: str) -> Optional[str]:
        """
        Return the Band chat_id for (room, agent), creating it on first use with
        that agent's OWN key. Returns None if the agent has no Band identity or
        the API is unavailable.
        """
        if not self._available or not self._http:
            return None

        canon = _canonical(agent_name)
        if not canon:
            return None  # Orchestrator / Adjudicator etc. — in-memory only.

        chats = self._agent_chats.setdefault(room_id, {})
        if canon in chats:
            return chats[canon]

        key = self.agent_keys.get(canon)
        if not key:
            return None

        try:
            resp = await self._http.post(
                "/agent/chats",
                headers={"X-API-Key": key},
                json={"chat": {"title": f"VerdictFlow · {agent_name} · {room_id}"}},
            )
            resp.raise_for_status()
            data = resp.json().get("data", resp.json())
            chat_id = str(data.get("id") or data.get("chat_id") or "")
            if chat_id:
                chats[canon] = chat_id
                logger.info(f"🧵 Band chat created for '{agent_name}' → {chat_id} (room {room_id})")
                return chat_id
        except Exception as e:
            logger.warning(f"⚠️  Could not create Band chat for '{agent_name}': {e}")
        return None

    # ── Band REST API: Send Message (to the agent's OWN chat) ────────────────

    async def send_agent_message(self, room_id: str, agent_name: str, message: str) -> bool:
        """Post a message to the agent's own Band chat and mirror it in-memory."""
        # Always mirror locally (authoritative for the UI/audit).
        self._record_message(room_id, agent_name, message)

        chat_id = await self._ensure_agent_chat(room_id, agent_name)
        if chat_id and self._http:
            canon = _canonical(agent_name)
            key = self.agent_keys.get(canon) if canon else None
            if key:
                try:
                    resp = await self._http.post(
                        f"/agent/chats/{chat_id}/events",
                        headers={"X-API-Key": key},
                        json={
                            "event": {
                                "content": message,
                                "message_type": "thought",
                                "metadata": {"agent": agent_name, "source": "verdictflow"},
                            }
                        },
                    )
                    if resp.status_code in (200, 201):
                        logger.debug(f"💬 {agent_name} → Band chat '{chat_id}'")
                    else:
                        logger.warning(
                            f"⚠️  Band send_message HTTP {resp.status_code} for '{agent_name}': "
                            f"{resp.text[:160]}"
                        )
                except Exception as e:
                    logger.warning(f"⚠️  Band send_message failed for '{agent_name}': {e}")
        else:
            logger.info(f"💬 {agent_name} → room '{room_id}' (in-memory): {message[:80]}...")

        return True

    # ── Band REST API: Send Event ────────────────────────────────────────────

    async def send_event(self, room_id: str, event_type: str, payload: dict[str, Any]) -> bool:
        """
        Record a structured stage event. Mirrored in-memory; also posted to the
        lead (Intake) agent's chat as a coordination note when available.
        """
        self._record_event(room_id, event_type, payload)

        chat_id = await self._ensure_agent_chat(room_id, "Intake Agent")
        if chat_id and self._http:
            key = self.agent_keys.get("intake agent")
            if key:
                try:
                    await self._http.post(
                        f"/agent/chats/{chat_id}/events",
                        headers={"X-API-Key": key},
                        json={
                            "event": {
                                "content": f"[event] {event_type}: {payload}",
                                "message_type": "thought",
                                "metadata": {"event_type": event_type, **payload},
                            }
                        },
                    )
                except Exception as e:
                    logger.warning(f"⚠️  Band send_event failed: {e}")
        else:
            logger.info(f"📡 Event '{event_type}' → room '{room_id}' (in-memory)")

        return True

    # ── Band REST API: Get Room History ──────────────────────────────────────

    async def get_room_history(self, room_id: str, limit: int = 50) -> list[dict]:
        """
        Return the unified conversation history for a case. The in-memory mirror
        is authoritative because it aggregates every agent's messages (Band
        chats are per-agent and cannot be queried as one room).
        """
        room = self._rooms.get(room_id)
        return room["messages"][-limit:] if room else []
