"""
VerdictFlow — Pydantic Domain Schemas

All domain models for contract analysis findings, agent outputs,
and the final audit packet.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

import uuid


# ── Enums ────────────────────────────────────────────────────────────────────


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NEEDS_REVIEW = "needs_review"


class EditPriority(str, Enum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class CaseStatus(str, Enum):
    UPLOADING = "uploading"
    INTAKE = "intake"
    ANALYZING = "analyzing"  # Clause + Red Team + Financial (parallel)
    COMPLIANCE = "compliance"
    REDLINING = "redlining"
    ADJUDICATING = "adjudicating"  # Final verdict synthesis
    AWAITING_REVIEW = "awaiting_review"  # Human gate
    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"


class Verdict(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_CHANGES = "approve_with_changes"
    DO_NOT_SIGN = "do_not_sign"


# ── Tolerant Enum Coercion ───────────────────────────────────────────────────
# LLMs occasionally return enum values with different casing, whitespace, or
# near-synonyms. These helpers map such values to a valid enum member instead of
# dropping the finding entirely.

_RISK_SYNONYMS = {
    "negligible": RiskLevel.LOW, "minimal": RiskLevel.LOW, "minor": RiskLevel.LOW,
    "moderate": RiskLevel.MEDIUM, "med": RiskLevel.MEDIUM,
    "severe": RiskLevel.HIGH, "serious": RiskLevel.HIGH, "major": RiskLevel.HIGH,
    "extreme": RiskLevel.CRITICAL, "fatal": RiskLevel.CRITICAL, "blocker": RiskLevel.CRITICAL,
}


def coerce_risk_level(value, default: RiskLevel = RiskLevel.MEDIUM) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    key = str(value or "").strip().lower()
    for member in RiskLevel:
        if key == member.value:
            return member
    return _RISK_SYNONYMS.get(key, default)


def coerce_compliance_status(value, default: "ComplianceStatus" = None) -> "ComplianceStatus":
    default = default or ComplianceStatus.NEEDS_REVIEW
    if isinstance(value, ComplianceStatus):
        return value
    key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    for member in ComplianceStatus:
        if key == member.value:
            return member
    if "non" in key and "compli" in key:
        return ComplianceStatus.NON_COMPLIANT
    if "compli" in key:
        return ComplianceStatus.COMPLIANT
    return default


def coerce_edit_priority(value, default: "EditPriority" = None) -> "EditPriority":
    default = default or EditPriority.RECOMMENDED
    if isinstance(value, EditPriority):
        return value
    key = str(value or "").strip().lower()
    for member in EditPriority:
        if key == member.value:
            return member
    if key in ("must", "critical", "mandatory"):
        return EditPriority.REQUIRED
    if key in ("nice_to_have", "nice-to-have", "consider", "suggested"):
        return EditPriority.OPTIONAL
    return default


# ── Contract Metadata ────────────────────────────────────────────────────────


class ContractMetadata(BaseModel):
    """Metadata extracted by the Intake Agent."""

    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    upload_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    page_count: int = 0
    total_chars: int = 0
    doc_type: str = "unknown"  # NDA, SaaS Agreement, Employment, etc.
    parties: list[str] = Field(default_factory=list)
    effective_date: Optional[str] = None
    governing_law: Optional[str] = None
    key_terms_summary: Optional[str] = None


# ── Agent Finding Models ─────────────────────────────────────────────────────


class ClauseFinding(BaseModel):
    """A finding from the Clause Analyst agent."""

    clause_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    clause_text: str
    category: str  # liability, termination, IP, indemnification, etc.
    risk_level: RiskLevel
    explanation: str
    agent_source: str = "clause_analyst"
    recommendations: list[str] = Field(default_factory=list)
    page_number: Optional[int] = None


class RedTeamAttack(BaseModel):
    """An adversarial finding from the Red Team agent."""

    attack_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attack_vector: str  # ambiguity, missing_clause, conflict, loophole
    target_clause: str
    exploit_scenario: str
    severity: RiskLevel
    agent_source: str = "red_team"
    defender_assessment: Optional[str] = None  # Defender agent's validation


class FinancialRisk(BaseModel):
    """A financial risk identified by the Financial Risk agent."""

    risk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str  # penalty, liability_cap, payment_terms, auto_renewal
    exposure_amount: Optional[float] = None
    currency: str = "USD"
    explanation: str
    risk_score: float = 0.0  # 0.0 - 1.0
    agent_source: str = "financial_risk"
    page_number: Optional[int] = None


class ComplianceCheck(BaseModel):
    """A compliance check from the Compliance agent."""

    check_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    regulation: str  # GDPR, SOX, HIPAA, CCPA, etc.
    status: ComplianceStatus
    finding: str
    remediation: str = ""
    agent_source: str = "compliance"
    relevant_clause: Optional[str] = None


class RedlineEdit(BaseModel):
    """A suggested edit from the Redline agent."""

    edit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_text: str
    suggested_text: str
    rationale: str
    priority: EditPriority
    agent_source: str = "redline"
    related_finding_ids: list[str] = Field(default_factory=list)


# ── Human Gate ───────────────────────────────────────────────────────────────


class HumanApproval(BaseModel):
    """Record of human gate decision."""

    approved: bool
    reviewer_name: Optional[str] = None
    feedback: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Audit Packet ─────────────────────────────────────────────────────────────


class AuditPacket(BaseModel):
    """
    The complete, tamper-evident audit packet.

    Contains all agent findings, the human gate decision, and
    the cryptographic hash chain proving data integrity.
    """

    case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: CaseStatus = CaseStatus.UPLOADING
    contract: Optional[ContractMetadata] = None
    clause_findings: list[ClauseFinding] = Field(default_factory=list)
    red_team_attacks: list[RedTeamAttack] = Field(default_factory=list)
    financial_risks: list[FinancialRisk] = Field(default_factory=list)
    compliance_checks: list[ComplianceCheck] = Field(default_factory=list)
    redline_edits: list[RedlineEdit] = Field(default_factory=list)
    # ── Adjudicator output (final synthesis before the human gate) ──
    verdict: Optional[str] = None  # 3-paragraph narrative verdict
    verdict_recommendation: Optional[Verdict] = None  # APPROVE / APPROVE_WITH_CHANGES / DO_NOT_SIGN
    confidence_score: float = 0.0  # 0.0 - 1.0
    human_approval: Optional[HumanApproval] = None
    audit_hash_chain: list[dict] = Field(default_factory=list)  # Populated from AuditChain
    band_room_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finalized_at: Optional[datetime] = None

    # ── Risk Summary (computed) ──

    @property
    def risk_summary(self) -> dict:
        """Compute aggregate risk statistics."""
        clause_risks = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for f in self.clause_findings:
            clause_risks[f.risk_level.value] += 1

        attack_severities = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for a in self.red_team_attacks:
            attack_severities[a.severity.value] += 1

        compliance_status = {"compliant": 0, "non_compliant": 0, "needs_review": 0}
        for c in self.compliance_checks:
            compliance_status[c.status.value] += 1

        total_financial_exposure = sum(
            r.exposure_amount for r in self.financial_risks if r.exposure_amount
        )

        return {
            "clause_risks": clause_risks,
            "attack_severities": attack_severities,
            "compliance_status": compliance_status,
            "total_financial_exposure": total_financial_exposure,
            "total_findings": (
                len(self.clause_findings)
                + len(self.red_team_attacks)
                + len(self.financial_risks)
                + len(self.compliance_checks)
            ),
            "total_redline_edits": len(self.redline_edits),
        }


# ── SSE Event Models ─────────────────────────────────────────────────────────


class SSEEvent(BaseModel):
    """A Server-Sent Event for real-time streaming."""

    event_type: str
    case_id: str
    data: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
