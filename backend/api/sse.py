"""
VerdictFlow — SSE Event Manager

In-memory event bus for Server-Sent Events per case.
Pushes real-time updates to all connected frontend clients.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

logger = logging.getLogger("verdictflow.sse")


class SSEManager:
    """
    Server-Sent Events manager for real-time case progress streaming.

    Maintains per-case event queues. Multiple clients can subscribe
    to the same case_id and receive events independently.
    """

    def __init__(self):
        # case_id → list of asyncio.Queue (one per connected client)
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        # case_id → list of past events (for catch-up on reconnect)
        self._event_history: dict[str, list[dict]] = {}

    def subscribe(self, case_id: str) -> asyncio.Queue:
        """
        Subscribe to events for a specific case.

        Returns an asyncio.Queue that will receive all future events
        for this case_id.
        """
        if case_id not in self._subscribers:
            self._subscribers[case_id] = []

        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[case_id].append(queue)

        logger.info(f"📺 New SSE subscriber for case '{case_id}' (total: {len(self._subscribers[case_id])})")
        return queue

    def unsubscribe(self, case_id: str, queue: asyncio.Queue):
        """Remove a subscriber's queue."""
        if case_id in self._subscribers:
            try:
                self._subscribers[case_id].remove(queue)
                logger.info(f"📺 SSE subscriber removed for case '{case_id}'")
            except ValueError:
                pass

            if not self._subscribers[case_id]:
                del self._subscribers[case_id]

    async def emit(
        self,
        case_id: str,
        event_type: str,
        data: Optional[dict] = None,
    ):
        """
        Emit an SSE event to all subscribers for a case.

        Args:
            case_id: The case to emit to
            event_type: Event type (e.g., "agent_started", "finding_added")
            data: Event payload data
        """
        event = {
            "event_type": event_type,
            "case_id": case_id,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Store in history
        if case_id not in self._event_history:
            self._event_history[case_id] = []
        self._event_history[case_id].append(event)

        # Push to all subscribers
        if case_id in self._subscribers:
            for queue in self._subscribers[case_id]:
                try:
                    await queue.put(event)
                except Exception:
                    pass

        logger.debug(f"📡 SSE emit: {event_type} → case '{case_id}'")

    def get_history(self, case_id: str) -> list[dict]:
        """Get all past events for a case (for catch-up on reconnect)."""
        return self._event_history.get(case_id, [])

    async def stream_events(
        self,
        case_id: str,
        include_history: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE-formatted event strings.

        Use this with FastAPI's StreamingResponse for SSE endpoints.
        """
        queue = self.subscribe(case_id)

        try:
            # Send catch-up history
            if include_history:
                for event in self.get_history(case_id):
                    yield f"data: {json.dumps(event)}\n\n"

            # Stream new events
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"

                    # Check for terminal events
                    if event.get("event_type") in ("case_finalized", "case_error"):
                        break

                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield ": keepalive\n\n"

        finally:
            self.unsubscribe(case_id, queue)


# ── Global SSE Manager Instance ──────────────────────────────────────────────

sse_manager = SSEManager()
