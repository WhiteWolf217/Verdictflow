"""
VerdictFlow — Band REST API Client

Connects to Band.ai via their REST API (Agent API at /api/v1/agent).
No SDK dependency — uses httpx for HTTP calls.

Key endpoints used:
- POST /agent/chats          → create chat rooms
- POST /agent/chats/{id}/messages  → send messages
- POST /agent/chats/{id}/events    → post events (tool calls, thoughts)
- GET  /agent/me             → verify agent identity
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger("verdictflow.band")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BandClientWrapper:
    """
    Direct REST integration with Band.ai Agent API.

    Creates shared chat rooms where agents post messages and events.
    Falls back to in-memory transcript when API key is missing
    or API calls fail.
    """

    def __init__(self):
        # Default Orchestrator Key
        self.api_key = os.getenv("BAND_API_KEY", "")
        self.agent_id = os.getenv("BAND_AGENT_ID", "")
        
        # Specific Agent Keys
        self.agent_keys = {
            "Intake Agent": os.getenv("BAND_INTAKE_KEY", ""),
            "Clause Analyst": os.getenv("BAND_CLAUSE_KEY", ""),
            "Red Team": os.getenv("BAND_REDTEAM_KEY", ""),
            "Compliance": os.getenv("BAND_COMPLIANCE_KEY", ""),
            "Financial Risk": os.getenv("BAND_FINANCIAL_KEY", ""),
            "Redline": os.getenv("BAND_REDLINE_KEY", ""),
            "Adjudicator": os.getenv("BAND_API_KEY", ""), # Adjudicator uses Orchestrator key
            "Orchestrator": os.getenv("BAND_API_KEY", ""),
        }

        self.workspace_id = os.getenv("BAND_WORKSPACE_ID", "")
        self.rest_url = os.getenv("BAND_REST_URL", "https://app.band.ai").rstrip("/")
        self.base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

        self._available = False
        self._http: Optional[httpx.AsyncClient] = None

        # In-memory transcript mirror: room_id → {name, case_id, messages, events}
        self._rooms: dict[str, dict] = {}

        if self.api_key and self.agent_id:
            self._http = httpx.AsyncClient(
                base_url=f"{self.rest_url}/api/v1",
                headers={
                    "Content-Type": "application/json",
                },
                timeout=15.0,
            )
            self._available = True
            logger.info(f"✅ Band REST client initialised (agent={self.agent_id[:8]}...)")
        else:
            logger.info(
                "ℹ️  BAND_API_KEY or BAND_AGENT_ID not set — "
                "using in-memory case rooms (demo mode)."
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

    async def verify_identity(self) -> Optional[dict]:
        """Verify the agent is properly connected to Band."""
        if not self._available or not self._http:
            return None
        try:
            resp = await self._http.get("/agent/me", headers={"X-API-Key": self.api_key})
            resp.raise_for_status()
            raw = resp.json()
            # Band wraps response in {"data": {...}}
            data = raw.get("data", raw)
            logger.info(f"✅ Band identity verified: {data.get('name', 'Unknown')} ({data.get('handle', '')})")
            return data
        except Exception as e:
            logger.warning(f"⚠️  Band identity verification failed: {e}")
            return None

    # ── Band REST API: Create Case Room ──────────────────────────────────────

    async def create_case_room(
        self,
        case_id: str,
        contract_name: str,
    ) -> Optional[str]:
        """
        Create a shared Band chat room for a contract review case.

        Returns Room ID if successful.
        """
        room_id = f"room_{case_id[:8]}"

        if self._available and self._http:
            try:
                resp = await self._http.post(
                    "/agent/chats",
                    json={"chat": {}},
                    headers={"X-API-Key": self.api_key}
                )
                resp.raise_for_status()
                raw = resp.json()
                data = raw.get("data", raw)
                band_room_id = data.get("id") or data.get("chat_id")
                if band_room_id:
                    room_id = str(band_room_id)
                logger.info(f"🏠 Created Band chat room '{room_id}' for case '{case_id}'")
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ Band create_case_room HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                logger.error(f"❌ Band create_case_room failed: {e}. Using in-memory room.")

        # Always register in-memory transcript
        self._rooms[room_id] = {
            "name": f"VerdictFlow Case: {contract_name}",
            "case_id": case_id,
            "band_room_id": room_id,
            "messages": [],
            "events": [],
            "created_at": _now(),
        }
        self._record_message(
            room_id, "System",
            f"📋 Case room opened for '{contract_name}'. Agents assembling...",
        )
        logger.info(f"🏠 Case room '{room_id}' ready ({self.mode}) for case '{case_id}'")
        return room_id

    # ── Band REST API: Add Agent ─────────────────────────────────────────────

    async def add_agent_to_room(
        self,
        room_id: str,
        agent_name: str,
    ) -> bool:
        """Register an agent as a participant in the case room."""
        if self._available and self._http:
            try:
                # Add using the specific agent's API key if available, otherwise fallback
                api_key = self.agent_keys.get(agent_name, self.api_key)
                # Note: Currently not possible to add other agents to a room via Agent API if we don't know their ID.
                # However, with Human API we would just create the room. 
                # Let's just log this for now, agents can just send messages.
                logger.info(f"👤 Simulated adding agent '{agent_name}' to Band room '{room_id}'")
            except Exception as e:
                logger.warning(f"⚠️  Failed to add agent to Band room: {e}")

        self._record_message(room_id, "System", f"Agent '{agent_name}' joined the room.")
        return True

    # ── Band REST API: Send Message ──────────────────────────────────────────

    async def send_agent_message(
        self,
        room_id: str,
        agent_name: str,
        message: str,
    ) -> bool:
        """
        Post a message to the case room on behalf of an agent.
        """
        # Always record locally
        self._record_message(room_id, agent_name, message)

        if self._available and self._http:
            try:
                api_key = self.agent_keys.get(agent_name, self.api_key)
                resp = await self._http.post(
                    f"/agent/chats/{room_id}/events",
                    headers={"X-API-Key": api_key},
                    json={
                        "event": {
                            "content": f"[{agent_name}] {message}",
                            "message_type": "thought",
                            "metadata": {
                                "agent": agent_name,
                                "source": "verdictflow",
                            },
                        }
                    },
                )
                if resp.status_code not in (200, 201):
                    logger.warning(f"⚠️  Band send_message HTTP {resp.status_code}: {resp.text[:200]}")
                else:
                    logger.debug(f"💬 {agent_name} → Band room '{room_id}'")
            except Exception as e:
                logger.warning(f"⚠️  Band send_message failed: {e}")
        else:
            logger.info(f"💬 {agent_name} → room '{room_id}': {message[:80]}...")

        return True

    # ── Band REST API: Send Event ────────────────────────────────────────────

    async def send_event(
        self,
        room_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """
        Post a structured event to the case room.
        """
        self._record_event(room_id, event_type, payload)

        if self._available and self._http:
            try:
                # Events usually come from the orchestrator
                api_key = self.api_key
                resp = await self._http.post(
                    f"/agent/chats/{room_id}/events",
                    headers={"X-API-Key": api_key},
                    json={
                        "event": {
                            "content": str(payload),
                            "message_type": event_type.lower(),
                            "metadata": payload,
                        }
                    },
                )
                if resp.status_code not in (200, 201):
                    logger.warning(f"⚠️  Band send_event HTTP {resp.status_code}: {resp.text[:200]}")
                else:
                    logger.debug(f"📡 Event '{event_type}' → Band room '{room_id}'")
            except Exception as e:
                logger.warning(f"⚠️  Band send_event failed: {e}")
        else:
            logger.info(f"📡 Event '{event_type}' → room '{room_id}'")

        return True

    # ── Band REST API: Get Room History ──────────────────────────────────────

    async def get_room_history(
        self,
        room_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """Retrieve conversation history from a case room."""
        if self._available and self._http:
            try:
                resp = await self._http.get(
                    f"/agent/chats/{room_id}/messages",
                    params={"limit": limit},
                    headers={"X-API-Key": self.api_key}
                )
                resp.raise_for_status()
                data = resp.json()
                return data if isinstance(data, list) else data.get("messages", data.get("data", []))
            except Exception as e:
                logger.warning(f"⚠️  Band get_room_history failed: {e}. Using local mirror.")

        # Fallback to in-memory
        room = self._rooms.get(room_id)
        return room["messages"][-limit:] if room else []
