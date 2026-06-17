"""
VerdictFlow — LangGraph Orchestrator

Sequences the 6-agent pipeline using a state graph:

    INTAKE → [CLAUSE_ANALYST | RED_TEAM | FINANCIAL_RISK] → COMPLIANCE → REDLINE → HUMAN_GATE

Parallel fan-out for the analysis phase (Clause, Red Team, Financial),
then fan-in for Compliance and Redline. The graph pauses at the
human gate checkpoint, awaiting approval via API.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from models.schemas import (
    AuditPacket,
    CaseStatus,
    ContractMetadata,
    HumanApproval,
)
from models.audit import AuditChain
from api.sse import sse_manager

logger = logging.getLogger("verdictflow.orchestrator")


# ── In-Memory Case Store ────────────────────────────────────────────────────
# In production, this would be a database. For the hackathon, in-memory is fine.

_cases: dict[str, AuditPacket] = {}
_audit_chains: dict[str, AuditChain] = {}
_contract_texts: dict[str, str] = {}  # case_id → raw contract text


def get_case(case_id: str) -> Optional[AuditPacket]:
    """Retrieve a case by ID."""
    return _cases.get(case_id)


def get_all_cases() -> list[AuditPacket]:
    """Retrieve all cases."""
    return list(_cases.values())


def get_audit_chain(case_id: str) -> Optional[AuditChain]:
    """Retrieve the audit chain for a case."""
    return _audit_chains.get(case_id)


# ── Orchestrator ─────────────────────────────────────────────────────────────


async def run_pipeline(
    case_id: str,
    file_path: str,
    filename: str,
    vectorstore=None,
    band_client=None,
) -> AuditPacket:
    """
    Run the full VerdictFlow pipeline for a contract.

    This is the main orchestration function that sequences all 6 agents,
    emits SSE events at each stage, and builds the tamper-evident audit trail.

    Args:
        case_id: Unique case identifier
        file_path: Path to the uploaded contract file
        filename: Original filename
        vectorstore: VectorStoreManager instance
        band_client: BandClientWrapper instance (optional)

    Returns:
        The completed AuditPacket
    """
    logger.info(f"🚀 Pipeline starting for case '{case_id}': {filename}")

    # Initialize case
    packet = AuditPacket(case_id=case_id)
    _cases[case_id] = packet

    audit_chain = AuditChain()
    _audit_chains[case_id] = audit_chain

    # Create Band case room (if available)
    room_id = None
    if band_client:
        room_id = await band_client.create_case_room(case_id, filename)
        packet.band_room_id = room_id

    try:
        # ── Stage 1: INTAKE ──────────────────────────────────────────────
        packet.status = CaseStatus.INTAKE
        await sse_manager.emit(case_id, "agent_started", {
            "agent": "intake", "message": "Processing document..."
        })

        from agents.intake_agent import run_intake_agent
        metadata, parsed_doc, chunks = await run_intake_agent(
            file_path, filename, vectorstore
        )
        packet.contract = metadata
        _contract_texts[case_id] = parsed_doc.raw_text

        audit_chain.add_entry(
            "intake_agent", "intake_complete",
            metadata.model_dump(mode="json"),
            summary=f"Parsed {filename}: {metadata.page_count} pages, type={metadata.doc_type}"
        )

        await sse_manager.emit(case_id, "agent_completed", {
            "agent": "intake",
            "message": f"Document classified as {metadata.doc_type}",
            "metadata": metadata.model_dump(mode="json"),
        })

        if band_client and room_id:
            await band_client.send_agent_message(
                room_id, "Intake Agent",
                f"✅ Processed '{filename}': {metadata.page_count} pages, "
                f"type={metadata.doc_type}, parties={metadata.parties}"
            )

        # ── Stage 2: PARALLEL ANALYSIS (Clause + Red Team + Financial) ───
        packet.status = CaseStatus.ANALYZING
        await sse_manager.emit(case_id, "stage_started", {
            "stage": "analysis",
            "message": "Running parallel analysis (Clause, Red Team, Financial)..."
        })

        contract_text = parsed_doc.raw_text

        # Run three agents concurrently
        from agents.clause_analyst import run_clause_analyst
        from agents.red_team_agent import run_red_team_agent
        from agents.financial_risk_agent import run_financial_risk_agent

        # Emit start events for each parallel agent
        for agent_name in ["clause_analyst", "red_team", "financial_risk"]:
            await sse_manager.emit(case_id, "agent_started", {
                "agent": agent_name,
                "message": f"{agent_name.replace('_', ' ').title()} analyzing..."
            })

        # Execute in parallel
        clause_task = asyncio.create_task(
            run_clause_analyst(metadata.doc_id, contract_text, vectorstore)
        )
        red_team_task = asyncio.create_task(
            run_red_team_agent(contract_text)
        )
        financial_task = asyncio.create_task(
            run_financial_risk_agent(contract_text)
        )

        # Wait for all three
        clause_findings, red_team_attacks, financial_risks = await asyncio.gather(
            clause_task, red_team_task, financial_task,
            return_exceptions=True,
        )

        # Handle potential exceptions
        if isinstance(clause_findings, Exception):
            logger.error(f"❌ Clause Analyst error: {clause_findings}")
            clause_findings = []
        if isinstance(red_team_attacks, Exception):
            logger.error(f"❌ Red Team error: {red_team_attacks}")
            red_team_attacks = []
        if isinstance(financial_risks, Exception):
            logger.error(f"❌ Financial Risk error: {financial_risks}")
            financial_risks = []

        packet.clause_findings = clause_findings
        packet.red_team_attacks = red_team_attacks
        packet.financial_risks = financial_risks

        # Audit entries for each
        audit_chain.add_entry(
            "clause_analyst", "clause_analysis_complete",
            [f.model_dump(mode="json") for f in clause_findings],
            summary=f"Found {len(clause_findings)} clause findings"
        )
        audit_chain.add_entry(
            "red_team", "red_team_complete",
            [a.model_dump(mode="json") for a in red_team_attacks],
            summary=f"Found {len(red_team_attacks)} attack vectors"
        )
        audit_chain.add_entry(
            "financial_risk", "financial_risk_complete",
            [r.model_dump(mode="json") for r in financial_risks],
            summary=f"Found {len(financial_risks)} financial risks"
        )

        # Emit completion events
        for agent, findings_list, label in [
            ("clause_analyst", clause_findings, "clause findings"),
            ("red_team", red_team_attacks, "attack vectors"),
            ("financial_risk", financial_risks, "financial risks"),
        ]:
            await sse_manager.emit(case_id, "agent_completed", {
                "agent": agent,
                "message": f"Found {len(findings_list)} {label}",
                "count": len(findings_list),
            })

        if band_client and room_id:
            await band_client.send_agent_message(
                room_id, "Orchestrator",
                f"📊 Analysis complete: {len(clause_findings)} clause findings, "
                f"{len(red_team_attacks)} attack vectors, {len(financial_risks)} financial risks"
            )

        # ── Stage 3: COMPLIANCE ──────────────────────────────────────────
        packet.status = CaseStatus.COMPLIANCE
        await sse_manager.emit(case_id, "agent_started", {
            "agent": "compliance",
            "message": "Running compliance checks..."
        })

        from agents.compliance_agent import run_compliance_agent
        compliance_checks = await run_compliance_agent(
            contract_text,
            doc_type=metadata.doc_type,
            governing_law=metadata.governing_law,
        )
        packet.compliance_checks = compliance_checks

        audit_chain.add_entry(
            "compliance", "compliance_complete",
            [c.model_dump(mode="json") for c in compliance_checks],
            summary=f"Performed {len(compliance_checks)} compliance checks"
        )

        await sse_manager.emit(case_id, "agent_completed", {
            "agent": "compliance",
            "message": f"Completed {len(compliance_checks)} compliance checks",
            "count": len(compliance_checks),
        })

        # ── Stage 4: REDLINE ─────────────────────────────────────────────
        packet.status = CaseStatus.REDLINING
        await sse_manager.emit(case_id, "agent_started", {
            "agent": "redline",
            "message": "Generating redline edits..."
        })

        from agents.redline_agent import run_redline_agent
        redline_edits = await run_redline_agent(
            contract_text,
            clause_findings,
            red_team_attacks,
            financial_risks,
            compliance_checks,
        )
        packet.redline_edits = redline_edits

        audit_chain.add_entry(
            "redline", "redline_complete",
            [e.model_dump(mode="json") for e in redline_edits],
            summary=f"Generated {len(redline_edits)} redline edits"
        )

        await sse_manager.emit(case_id, "agent_completed", {
            "agent": "redline",
            "message": f"Generated {len(redline_edits)} redline edits",
            "count": len(redline_edits),
        })

        # ── Stage 5: HUMAN GATE ──────────────────────────────────────────
        packet.status = CaseStatus.AWAITING_REVIEW
        packet.audit_hash_chain = audit_chain.export_json()

        await sse_manager.emit(case_id, "gate_requested", {
            "message": "Review required — all analysis complete",
            "risk_summary": packet.risk_summary,
        })

        if band_client and room_id:
            await band_client.send_agent_message(
                room_id, "Orchestrator",
                "🔒 All analysis complete. Awaiting human review and approval."
            )

        logger.info(f"✅ Pipeline complete for case '{case_id}' — awaiting human review")
        return packet

    except Exception as e:
        logger.error(f"❌ Pipeline error for case '{case_id}': {e}")
        packet.status = CaseStatus.ERROR
        await sse_manager.emit(case_id, "case_error", {
            "message": str(e),
        })
        raise


async def approve_case(case_id: str, feedback: Optional[str] = None) -> AuditPacket:
    """Approve a case at the human gate."""
    packet = _cases.get(case_id)
    if not packet:
        raise ValueError(f"Case '{case_id}' not found")

    packet.human_approval = HumanApproval(
        approved=True,
        feedback=feedback,
    )
    packet.status = CaseStatus.APPROVED
    packet.finalized_at = datetime.now(timezone.utc)

    # Add approval to audit chain
    audit_chain = _audit_chains.get(case_id)
    if audit_chain:
        audit_chain.add_entry(
            "human_gate", "approved",
            packet.human_approval.model_dump(mode="json"),
            summary="Case approved by human reviewer"
        )
        packet.audit_hash_chain = audit_chain.export_json()

    await sse_manager.emit(case_id, "case_finalized", {
        "status": "approved",
        "message": "Case approved and audit packet sealed",
    })

    logger.info(f"✅ Case '{case_id}' APPROVED")
    return packet


async def reject_case(case_id: str, feedback: Optional[str] = None) -> AuditPacket:
    """Reject a case at the human gate."""
    packet = _cases.get(case_id)
    if not packet:
        raise ValueError(f"Case '{case_id}' not found")

    packet.human_approval = HumanApproval(
        approved=False,
        feedback=feedback,
    )
    packet.status = CaseStatus.REJECTED
    packet.finalized_at = datetime.now(timezone.utc)

    audit_chain = _audit_chains.get(case_id)
    if audit_chain:
        audit_chain.add_entry(
            "human_gate", "rejected",
            packet.human_approval.model_dump(mode="json"),
            summary=f"Case rejected: {feedback or 'No feedback provided'}"
        )
        packet.audit_hash_chain = audit_chain.export_json()

    await sse_manager.emit(case_id, "case_finalized", {
        "status": "rejected",
        "message": f"Case rejected: {feedback or 'No feedback'}",
    })

    logger.info(f"❌ Case '{case_id}' REJECTED: {feedback}")
    return packet
