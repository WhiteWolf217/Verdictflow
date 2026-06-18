"""
VerdictFlow — Tamper-Evident Audit Trail

SHA-256 hash-chain implementation that cryptographically links each
agent's output to the previous entry. Provides integrity verification
and export capabilities for the audit packet.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("verdictflow.audit")


# ── Data Models ──────────────────────────────────────────────────────────────


class AuditEntry(BaseModel):
    """A single entry in the tamper-evident hash chain."""

    step_index: int
    agent_name: str
    action: str  # e.g., "intake_complete", "clause_finding_added"
    data_hash: str  # SHA-256 hash of the entry's data payload
    previous_hash: str  # Hash of the previous entry (chain link)
    current_hash: str  # SHA-256 hash of this entire entry
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_summary: Optional[str] = None  # Human-readable summary


# ── Hash Chain ───────────────────────────────────────────────────────────────


GENESIS_HASH = "0" * 64  # Genesis block — no previous entry


class AuditChain:
    """
    Tamper-evident audit trail using SHA-256 hash chaining.

    Each entry's hash includes:
    - The entry's own data (agent output)
    - The hash of the previous entry

    This creates an unbreakable chain where modifying any past entry
    invalidates all subsequent hashes.
    """

    def __init__(self):
        self.entries: list[AuditEntry] = []

    @staticmethod
    def _hash_data(data: Any) -> str:
        """Compute SHA-256 hash of arbitrary data."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_entry(
        step_index: int,
        agent_name: str,
        action: str,
        data_hash: str,
        previous_hash: str,
        timestamp: str,
    ) -> str:
        """
        Compute the hash of a complete audit entry.

        Includes all fields to ensure any tampering is detectable.
        """
        entry_str = json.dumps(
            {
                "step_index": step_index,
                "agent_name": agent_name,
                "action": action,
                "data_hash": data_hash,
                "previous_hash": previous_hash,
                "timestamp": timestamp,
            },
            sort_keys=True,
        )
        return hashlib.sha256(entry_str.encode("utf-8")).hexdigest()

    def add_entry(
        self,
        agent_name: str,
        action: str,
        data: Any,
        summary: Optional[str] = None,
    ) -> AuditEntry:
        """
        Add a new entry to the hash chain.

        Args:
            agent_name: Name of the agent producing this entry
            action: Description of the action (e.g., "clause_analysis_complete")
            data: The actual data/findings to hash (not stored, only hashed)
            summary: Human-readable summary for display

        Returns:
            The newly created AuditEntry
        """
        step_index = len(self.entries)
        previous_hash = (
            self.entries[-1].current_hash if self.entries else GENESIS_HASH
        )
        timestamp = datetime.now(timezone.utc)

        # Hash the data payload
        data_hash = self._hash_data(data)

        # Compute the entry's chain hash
        current_hash = self._hash_entry(
            step_index=step_index,
            agent_name=agent_name,
            action=action,
            data_hash=data_hash,
            previous_hash=previous_hash,
            timestamp=timestamp.isoformat(),
        )

        entry = AuditEntry(
            step_index=step_index,
            agent_name=agent_name,
            action=action,
            data_hash=data_hash,
            previous_hash=previous_hash,
            current_hash=current_hash,
            timestamp=timestamp,
            data_summary=summary,
        )

        self.entries.append(entry)

        logger.info(
            f"🔗 Audit entry #{step_index}: {agent_name}/{action} "
            f"→ {current_hash[:16]}..."
        )

        return entry

    def verify_integrity(self) -> tuple[bool, Optional[str]]:
        """
        Verify the entire hash chain for tamper evidence.

        Returns:
            Tuple of (is_valid, error_message).
            If valid, error_message is None.
        """
        if not self.entries:
            return True, None

        for i, entry in enumerate(self.entries):
            # Check step index
            if entry.step_index != i:
                return False, f"Step index mismatch at position {i}: expected {i}, got {entry.step_index}"

            # Check previous hash linkage
            expected_prev = (
                self.entries[i - 1].current_hash if i > 0 else GENESIS_HASH
            )
            if entry.previous_hash != expected_prev:
                return False, (
                    f"Chain broken at step {i}: "
                    f"expected prev_hash={expected_prev[:16]}..., "
                    f"got {entry.previous_hash[:16]}..."
                )

            # Recompute and verify the entry hash
            recomputed_hash = self._hash_entry(
                step_index=entry.step_index,
                agent_name=entry.agent_name,
                action=entry.action,
                data_hash=entry.data_hash,
                previous_hash=entry.previous_hash,
                timestamp=entry.timestamp.isoformat(),
            )

            if entry.current_hash != recomputed_hash:
                return False, (
                    f"Hash mismatch at step {i}: "
                    f"stored={entry.current_hash[:16]}..., "
                    f"computed={recomputed_hash[:16]}..."
                )

        logger.info(f"✅ Audit chain verified: {len(self.entries)} entries, integrity intact")
        return True, None

    def export_json(self) -> list[dict]:
        """Export the hash chain as a JSON-serializable list."""
        return [entry.model_dump(mode="json") for entry in self.entries]

    def get_latest_hash(self) -> str:
        """Get the hash of the most recent entry."""
        if self.entries:
            return self.entries[-1].current_hash
        return GENESIS_HASH

    def __len__(self) -> int:
        return len(self.entries)

    def __repr__(self) -> str:
        return f"AuditChain(entries={len(self.entries)}, latest_hash={self.get_latest_hash()[:16]}...)"
