"""
VerdictFlow — Observability Module

AgentOps integration for session tracing, token monitoring,
and agent execution tracking.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("verdictflow.observability")


def init_agentops() -> bool:
    """
    Initialize AgentOps for observability.

    Provides:
    - Session replay for agent execution flows
    - Token consumption tracking across all LLM calls
    - Agent-to-agent interaction tracing
    - Cost monitoring per case

    Returns:
        True if initialization was successful
    """
    api_key = os.getenv("AGENTOPS_API_KEY")
    if not api_key:
        logger.info("⏭️  AGENTOPS_API_KEY not set — observability disabled")
        return False

    try:
        import agentops

        agentops.init(
            api_key=api_key,
            default_tags=["verdictflow", "contract-review"],
        )
        logger.info("✅ AgentOps initialized for observability")
        return True

    except ImportError:
        logger.warning("⚠️  agentops package not installed")
        return False
    except Exception as e:
        logger.error(f"❌ AgentOps initialization failed: {e}")
        return False


def start_case_session(case_id: str) -> Optional[object]:
    """
    Start an AgentOps session for a case.

    Each case gets its own session for isolated tracking.
    """
    try:
        import agentops
        session = agentops.start_session(
            tags=["case", case_id],
        )
        logger.info(f"📊 AgentOps session started for case '{case_id}'")
        return session
    except Exception:
        return None


def end_case_session(session, status: str = "Success"):
    """End an AgentOps session."""
    if session is None:
        return
    try:
        import agentops
        session.end(end_state=status)
    except Exception:
        pass
