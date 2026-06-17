"""
VerdictFlow — Band SDK Client Wrapper

Provides a high-level interface for Band SDK operations:
creating case rooms, managing participants, sending messages
and events for inter-agent coordination.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("verdictflow.band")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BandClientWrapper:
    """
    Wrapper around the Band SDK for multi-agent coordination.

    Creates shared "case rooms" where agents communicate findings, status
    updates, and coordination events. Every room's messages and events are
    ALSO mirrored to an in-memory transcript, so the case room is fully
    demoable (and inspectable via the API) even when the external Band SDK
    is not installed — in that mode the wrapper is the room.
    """

    def __init__(self):
        self.api_key = os.getenv("BAND_API_KEY", "")
        self.workspace_id = os.getenv("BAND_WORKSPACE_ID", "")
        # Base URL used to build a shareable room link for the UI.
        self.base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
        self._client = None
        self._available = False

        # In-memory transcript: room_id → {name, case_id, messages, events, ...}
        self._rooms: dict[str, dict] = {}

        try:
            from band_sdk import BandClient

            self._client = BandClient(
                api_key=self.api_key,
                workspace_id=self.workspace_id,
            )
            self._available = True
            logger.info("✅ Band SDK client initialized")
        except ImportError:
            logger.info(
                "ℹ️  band-sdk not installed — using built-in in-memory case rooms "
                "(fully functional for coordination and demo)."
            )
        except Exception as e:
            logger.warning(f"⚠️  Band SDK initialization failed: {e}. Using in-memory case rooms.")

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def mode(self) -> str:
        return "band_sdk" if self._available else "in_memory"

    # ── In-memory transcript helpers ─────────────────────────────────────────

    def room_url(self, room_id: Optional[str]) -> Optional[str]:
        """Shareable URL for a case room's transcript."""
        if not room_id:
            return None
        return f"{self.base_url}/api/rooms/{room_id}"

    def get_transcript(self, room_id: str) -> Optional[dict]:
        """Return the full in-memory transcript for a room (or None)."""
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

    async def create_case_room(
        self,
        case_id: str,
        contract_name: str,
    ) -> Optional[str]:
        """
        Create a shared Band chatroom for a contract review case.

        Args:
            case_id: Unique case identifier
            contract_name: Name of the contract being reviewed

        Returns:
            Room ID if successful, None otherwise
        """
        room_id = f"room_{case_id[:8]}"

        if self._available:
            try:
                room = self._client.create_chatroom(
                    name=f"VerdictFlow Case: {contract_name}",
                    description=(
                        f"Contract review case room for '{contract_name}'. "
                        f"Case ID: {case_id}. "
                        "Agents will coordinate analysis, findings, and approvals here."
                    ),
                )
                room_id = room.get("id", room.get("room_id")) or room_id
                logger.info(f"🏠 Created Band room '{room_id}' for case '{case_id}'")
            except Exception as e:
                logger.error(f"❌ Failed to create Band room: {e}. Falling back to in-memory room.")

        # Always register the in-memory transcript so the room is inspectable.
        self._rooms[room_id] = {
            "name": f"VerdictFlow Case: {contract_name}",
            "case_id": case_id,
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

    async def add_agent_to_room(
        self,
        room_id: str,
        agent_name: str,
    ) -> bool:
        """Register an agent as a participant in the case room."""
        if not self._available:
            logger.info(f"🔇 [Band mock] Would add agent '{agent_name}' to room '{room_id}'")
            return True

        try:
            self._client.add_participant(
                room_id=room_id,
                participant_name=agent_name,
                role="agent",
            )
            logger.info(f"👤 Added agent '{agent_name}' to room '{room_id}'")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add agent to room: {e}")
            return False

    async def send_agent_message(
        self,
        room_id: str,
        agent_name: str,
        message: str,
    ) -> bool:
        """
        Post a message to the case room on behalf of an agent.

        Used for sharing findings, status updates, and commentary.
        """
        # Always record to the in-memory transcript.
        self._record_message(room_id, agent_name, message)
        logger.info(f"💬 {agent_name} → room '{room_id}': {message[:80]}...")

        if self._available:
            try:
                self._client.send_message(room_id=room_id, text=f"[{agent_name}] {message}")
            except Exception as e:
                logger.error(f"❌ Failed to send message to Band SDK: {e}")
        return True

    async def send_event(
        self,
        room_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """
        Broadcast a structured event to the case room.

        Used for inter-agent coordination signals like
        "INTAKE_COMPLETE", "CLAUSE_ANALYSIS_COMPLETE", etc.
        """
        self._record_event(room_id, event_type, payload)
        logger.info(f"📡 Event '{event_type}' → room '{room_id}'")

        if self._available:
            try:
                self._client.send_event(room_id=room_id, event_type=event_type, payload=payload)
            except Exception as e:
                logger.error(f"❌ Failed to send event to Band SDK: {e}")
        return True

    async def get_room_history(
        self,
        room_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """Retrieve conversation history from a case room."""
        room = self._rooms.get(room_id)
        messages = room["messages"][-limit:] if room else []

        # If the real SDK is available, prefer its authoritative history but
        # fall back to the in-memory mirror on any error.
        if self._available:
            try:
                return self._client.get_messages(room_id=room_id, limit=limit)
            except Exception as e:
                logger.error(f"❌ Failed to fetch Band SDK history: {e}. Using in-memory mirror.")

        return messages
