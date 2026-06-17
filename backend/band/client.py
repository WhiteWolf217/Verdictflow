"""
VerdictFlow — Band SDK Client Wrapper

Provides a high-level interface for Band SDK operations:
creating case rooms, managing participants, sending messages
and events for inter-agent coordination.
"""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("verdictflow.band")


class BandClientWrapper:
    """
    Wrapper around the Band SDK for multi-agent coordination.

    Creates shared "case rooms" where agents communicate findings,
    status updates, and coordination events.

    Gracefully degrades if Band SDK is unavailable — all methods
    become no-ops with logging.
    """

    def __init__(self):
        self.api_key = os.getenv("BAND_API_KEY", "")
        self.workspace_id = os.getenv("BAND_WORKSPACE_ID", "")
        self._client = None
        self._available = False

        try:
            from band_sdk import BandClient

            self._client = BandClient(
                api_key=self.api_key,
                workspace_id=self.workspace_id,
            )
            self._available = True
            logger.info("✅ Band SDK client initialized")
        except ImportError:
            logger.warning(
                "⚠️  band-sdk not installed. Running without Band coordination. "
                "Install with: pip install 'band-sdk[langgraph]'"
            )
        except Exception as e:
            logger.warning(f"⚠️  Band SDK initialization failed: {e}")

    @property
    def is_available(self) -> bool:
        return self._available

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
        if not self._available:
            logger.info(f"🔇 [Band mock] Would create room for case '{case_id}'")
            return f"mock_room_{case_id}"

        try:
            room = self._client.create_chatroom(
                name=f"VerdictFlow Case: {contract_name}",
                description=(
                    f"Contract review case room for '{contract_name}'. "
                    f"Case ID: {case_id}. "
                    "Agents will coordinate analysis, findings, and approvals here."
                ),
            )
            room_id = room.get("id", room.get("room_id"))
            logger.info(f"🏠 Created Band room '{room_id}' for case '{case_id}'")
            return room_id
        except Exception as e:
            logger.error(f"❌ Failed to create Band room: {e}")
            return f"mock_room_{case_id}"

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
        if not self._available:
            logger.info(f"🔇 [Band mock] {agent_name}: {message[:100]}...")
            return True

        try:
            self._client.send_message(
                room_id=room_id,
                text=f"[{agent_name}] {message}",
            )
            logger.info(f"💬 {agent_name} → room '{room_id}': {message[:80]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            return False

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
        if not self._available:
            logger.info(f"🔇 [Band mock] Event '{event_type}' → room '{room_id}'")
            return True

        try:
            self._client.send_event(
                room_id=room_id,
                event_type=event_type,
                payload=payload,
            )
            logger.info(f"📡 Event '{event_type}' → room '{room_id}'")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send event: {e}")
            return False

    async def get_room_history(
        self,
        room_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """Retrieve conversation history from a case room."""
        if not self._available:
            logger.info(f"🔇 [Band mock] Would fetch history for room '{room_id}'")
            return []

        try:
            history = self._client.get_messages(
                room_id=room_id,
                limit=limit,
            )
            return history
        except Exception as e:
            logger.error(f"❌ Failed to fetch room history: {e}")
            return []
