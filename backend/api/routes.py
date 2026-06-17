"""
VerdictFlow — FastAPI Routes

API endpoints for contract upload, case management, SSE streaming,
human gate operations, and audit trail verification.
"""

import asyncio
import logging
import os
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from api.sse import sse_manager

logger = logging.getLogger("verdictflow.api")

router = APIRouter()


# ── Request/Response Models ──────────────────────────────────────────────────


class ApprovalRequest(BaseModel):
    feedback: Optional[str] = None


class CaseListItem(BaseModel):
    case_id: str
    filename: str
    status: str
    doc_type: str
    created_at: str
    total_findings: int


# ── Upload Directory ─────────────────────────────────────────────────────────

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post("/contracts/upload")
async def upload_contract(request: Request, file: UploadFile = File(...)):
    """
    Upload a contract document (PDF or DOCX) and start the analysis pipeline.

    Returns the case_id immediately. Connect to the SSE stream to
    monitor progress.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    from core.parser import SUPPORTED_EXTENSIONS

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    # Generate case ID and save file
    case_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{case_id}{ext}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"📁 Uploaded '{file.filename}' → case '{case_id}'")

    # Get vectorstore and band client from app state
    vectorstore = getattr(request.app.state, "vectorstore", None)
    band_client = getattr(request.app.state, "band_client", None)

    # Start pipeline in background
    from agents.orchestrator import run_pipeline

    asyncio.create_task(
        run_pipeline(
            case_id=case_id,
            file_path=file_path,
            filename=file.filename,
            vectorstore=vectorstore,
            band_client=band_client,
        )
    )

    return {
        "case_id": case_id,
        "filename": file.filename,
        "status": "processing",
        "message": "Pipeline started. Connect to SSE stream for real-time updates.",
        "stream_url": f"/api/cases/{case_id}/stream",
    }


@router.get("/cases")
async def list_cases():
    """List all cases with their current status."""
    from agents.orchestrator import get_all_cases

    cases = get_all_cases()
    result = []

    for packet in cases:
        result.append({
            "case_id": packet.case_id,
            "filename": packet.contract.filename if packet.contract else "Unknown",
            "status": packet.status.value,
            "doc_type": packet.contract.doc_type if packet.contract else "unknown",
            "created_at": packet.created_at.isoformat(),
            "total_findings": packet.risk_summary.get("total_findings", 0) if packet.contract else 0,
        })

    # Sort by creation time (newest first)
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return {"cases": result}


@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    """Get the full case detail including all findings."""
    from agents.orchestrator import get_case

    packet = get_case(case_id)
    if not packet:
        raise HTTPException(404, f"Case '{case_id}' not found")

    return {
        "case_id": packet.case_id,
        "status": packet.status.value,
        "contract": packet.contract.model_dump(mode="json") if packet.contract else None,
        "clause_findings": [f.model_dump(mode="json") for f in packet.clause_findings],
        "red_team_attacks": [a.model_dump(mode="json") for a in packet.red_team_attacks],
        "financial_risks": [r.model_dump(mode="json") for r in packet.financial_risks],
        "compliance_checks": [c.model_dump(mode="json") for c in packet.compliance_checks],
        "redline_edits": [e.model_dump(mode="json") for e in packet.redline_edits],
        "verdict": packet.verdict,
        "verdict_recommendation": packet.verdict_recommendation.value if packet.verdict_recommendation else None,
        "confidence_score": packet.confidence_score,
        "human_approval": packet.human_approval.model_dump(mode="json") if packet.human_approval else None,
        "risk_summary": packet.risk_summary,
        "band_room_id": packet.band_room_id,
        "created_at": packet.created_at.isoformat(),
        "finalized_at": packet.finalized_at.isoformat() if packet.finalized_at else None,
    }


@router.get("/cases/{case_id}/stream")
async def stream_case(case_id: str):
    """
    SSE endpoint for real-time case progress streaming.

    Connect via EventSource to receive live updates as agents
    process the contract.
    """
    return StreamingResponse(
        sse_manager.stream_events(case_id, include_history=True),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/cases/{case_id}/approve")
async def approve_case(case_id: str, body: ApprovalRequest):
    """Approve a case at the human gate."""
    from agents.orchestrator import approve_case as _approve

    try:
        packet = await _approve(case_id, body.feedback)
        return {
            "case_id": packet.case_id,
            "status": "approved",
            "message": "Case approved. Audit packet sealed.",
            "finalized_at": packet.finalized_at.isoformat() if packet.finalized_at else None,
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/cases/{case_id}/reject")
async def reject_case(case_id: str, body: ApprovalRequest):
    """Reject a case at the human gate with optional feedback."""
    from agents.orchestrator import reject_case as _reject

    try:
        packet = await _reject(case_id, body.feedback)
        return {
            "case_id": packet.case_id,
            "status": "rejected",
            "message": "Case rejected.",
            "feedback": body.feedback,
            "finalized_at": packet.finalized_at.isoformat() if packet.finalized_at else None,
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/rooms/{room_id}")
async def get_room(room_id: str, request: Request):
    """Return the Band case-room transcript (agent conversation + events)."""
    band_client = getattr(request.app.state, "band_client", None)
    if not band_client:
        raise HTTPException(404, "Band coordination not available")

    transcript = band_client.get_transcript(room_id)
    if not transcript:
        raise HTTPException(404, f"Room '{room_id}' not found")
    return transcript


@router.get("/cases/{case_id}/room")
async def get_case_room(case_id: str, request: Request):
    """Resolve a case to its Band room and return the transcript."""
    from agents.orchestrator import get_case

    packet = get_case(case_id)
    if not packet:
        raise HTTPException(404, f"Case '{case_id}' not found")

    band_client = getattr(request.app.state, "band_client", None)
    if not band_client or not packet.band_room_id:
        raise HTTPException(404, "No room associated with this case")

    transcript = band_client.get_transcript(packet.band_room_id)
    if not transcript:
        raise HTTPException(404, "Room transcript not found")
    return transcript


@router.get("/cases/{case_id}/audit")
async def get_audit_trail(case_id: str):
    """Export the tamper-evident audit packet as JSON."""
    from agents.orchestrator import get_case, get_audit_chain

    packet = get_case(case_id)
    if not packet:
        raise HTTPException(404, f"Case '{case_id}' not found")

    audit_chain = get_audit_chain(case_id)

    return {
        "case_id": case_id,
        "status": packet.status.value,
        "audit_chain": audit_chain.export_json() if audit_chain else [],
        "chain_length": len(audit_chain) if audit_chain else 0,
        "latest_hash": audit_chain.get_latest_hash() if audit_chain else None,
    }


@router.get("/cases/{case_id}/download")
async def download_audit(case_id: str):
    """Download the audit packet as a professional .docx report."""
    from agents.orchestrator import get_case, get_audit_chain
    from core.audit_packager import build_audit_docx

    packet = get_case(case_id)
    if not packet:
        raise HTTPException(404, f"Case '{case_id}' not found")

    audit_chain = get_audit_chain(case_id)
    latest_hash = audit_chain.get_latest_hash() if audit_chain else None

    data = build_audit_docx(packet, latest_hash)
    filename = f"verdictflow_audit_{case_id[:8]}.docx"
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cases/{case_id}/audit/verify")
async def verify_audit_trail(case_id: str):
    """Verify the hash chain integrity of the audit trail."""
    from agents.orchestrator import get_audit_chain

    audit_chain = get_audit_chain(case_id)
    if not audit_chain:
        raise HTTPException(404, f"No audit chain found for case '{case_id}'")

    is_valid, error = audit_chain.verify_integrity()

    return {
        "case_id": case_id,
        "is_valid": is_valid,
        "chain_length": len(audit_chain),
        "latest_hash": audit_chain.get_latest_hash(),
        "error": error,
    }
