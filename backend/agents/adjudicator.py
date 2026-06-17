"""
VerdictFlow — Adjudicator Agent

Framework: Direct Anthropic API (Claude Sonnet 4.6)
Model: Claude Sonnet 4.6

The synthesis pass. After all analysis + redline agents run, the Adjudicator
reviews the full body of findings and issues a final verdict:

    APPROVE / APPROVE WITH CHANGES / DO NOT SIGN

plus a confidence score. The recommendation and confidence are computed
DETERMINISTICALLY from the findings (so they are always available, even if the
LLM narrative call fails), while Claude writes the human-readable verdict text.
"""

import logging
import os
from typing import TYPE_CHECKING

from models.schemas import Verdict

if TYPE_CHECKING:
    from models.schemas import AuditPacket

logger = logging.getLogger("verdictflow.agents.adjudicator")


ADJUDICATOR_SYSTEM_PROMPT = """You are the Chief Legal Counsel issuing a final contract
review verdict. You are given a structured summary of findings from a team of
specialized review agents and a pre-computed recommendation. Write a professional,
decisive 3-paragraph verdict:

Paragraph 1: Overall risk assessment and the recommendation (APPROVE / APPROVE WITH
CHANGES / DO NOT SIGN). State the recommendation explicitly.
Paragraph 2: The top issues requiring immediate attention.
Paragraph 3: Concrete next steps for the legal team.

Be direct and specific. Cite the actual numbers provided. Do not invent findings."""


def _compute_metrics(packet: "AuditPacket") -> dict:
    """Deterministic risk metrics from the packet's findings."""
    high_clauses = sum(
        1 for f in packet.clause_findings if f.risk_level.value in ("high", "critical")
    )
    critical_clauses = sum(1 for f in packet.clause_findings if f.risk_level.value == "critical")
    high_attacks = sum(
        1 for a in packet.red_team_attacks if a.severity.value in ("high", "critical")
    )
    critical_attacks = sum(1 for a in packet.red_team_attacks if a.severity.value == "critical")
    non_compliant = sum(
        1 for c in packet.compliance_checks if c.status.value == "non_compliant"
    )
    high_financial = sum(1 for r in packet.financial_risks if (r.risk_score or 0) >= 0.7)
    exposure = sum(r.exposure_amount for r in packet.financial_risks if r.exposure_amount)

    return {
        "high_clauses": high_clauses,
        "critical_clauses": critical_clauses,
        "high_attacks": high_attacks,
        "critical_attacks": critical_attacks,
        "non_compliant": non_compliant,
        "high_financial": high_financial,
        "exposure": exposure,
        "total_findings": (
            len(packet.clause_findings)
            + len(packet.red_team_attacks)
            + len(packet.financial_risks)
            + len(packet.compliance_checks)
        ),
        "redlines": len(packet.redline_edits),
    }


def _recommend(m: dict) -> Verdict:
    """Deterministic recommendation from metrics."""
    severe = m["critical_clauses"] + m["critical_attacks"] + m["non_compliant"]
    elevated = m["high_clauses"] + m["high_attacks"] + m["high_financial"]
    if severe > 0:
        return Verdict.DO_NOT_SIGN
    if elevated > 0 or m["redlines"] > 0 or m["total_findings"] > 0:
        return Verdict.APPROVE_WITH_CHANGES
    return Verdict.APPROVE


def _confidence(m: dict) -> float:
    """Deterministic confidence score in [0, 1]."""
    base = 0.7
    base += 0.1 if m["high_clauses"] + m["high_attacks"] < 3 else 0.0
    base += 0.1 if m["non_compliant"] == 0 else 0.0
    base += 0.1 if m["total_findings"] > 0 else 0.0  # found something = thorough review
    return round(min(base, 1.0), 2)


_REC_LABEL = {
    Verdict.APPROVE: "APPROVE",
    Verdict.APPROVE_WITH_CHANGES: "APPROVE WITH CHANGES",
    Verdict.DO_NOT_SIGN: "DO NOT SIGN",
}


def _fallback_verdict(m: dict, rec: Verdict, confidence: float) -> str:
    """Templated verdict used when the LLM narrative is unavailable."""
    exposure_str = f"${m['exposure']:,.0f}" if m["exposure"] else "not quantified"
    return (
        f"RECOMMENDATION: {_REC_LABEL[rec]} (confidence {confidence:.0%}).\n\n"
        f"This review surfaced {m['total_findings']} findings: "
        f"{m['high_clauses']} high/critical clause risks, {m['high_attacks']} high/critical "
        f"adversarial findings, {m['non_compliant']} compliance failures, and a total "
        f"financial exposure of {exposure_str}. {m['redlines']} redline edits have been "
        f"proposed to address the issues.\n\n"
        f"The legal team should review the proposed redlines, prioritise the required "
        f"edits, and resolve any compliance gaps before signing."
    )


async def run_adjudicator(packet: "AuditPacket") -> tuple[str, Verdict, float]:
    """
    Produce the final verdict for a case.

    Returns (verdict_text, recommendation, confidence_score). The recommendation
    and confidence are deterministic; only the narrative text depends on the LLM.
    """
    logger.info("⚖️  Adjudicator synthesizing final verdict...")

    m = _compute_metrics(packet)
    rec = _recommend(m)
    confidence = _confidence(m)

    # Build a compact findings digest for the narrative.
    top_clauses = "\n".join(
        f"- [{f.risk_level.value.upper()}] {f.category}: {f.explanation[:160]}"
        for f in packet.clause_findings[:5]
    ) or "None"
    top_compliance = "\n".join(
        f"- {c.regulation}: {c.finding[:160]}"
        for c in packet.compliance_checks
        if c.status.value == "non_compliant"
    )[:800] or "None"

    user_prompt = (
        f"PRE-COMPUTED RECOMMENDATION: {_REC_LABEL[rec]}\n"
        f"CONFIDENCE: {confidence:.0%}\n\n"
        f"SUMMARY OF FINDINGS:\n"
        f"- High/critical clause risks: {m['high_clauses']}\n"
        f"- High/critical adversarial findings: {m['high_attacks']}\n"
        f"- Compliance failures: {m['non_compliant']}\n"
        f"- Proposed redlines: {m['redlines']}\n"
        f"- Total financial exposure: ${m['exposure']:,.0f}\n\n"
        f"TOP CLAUSE RISKS:\n{top_clauses}\n\n"
        f"COMPLIANCE ISSUES:\n{top_compliance}\n"
    )

    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            system=ADJUDICATOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        verdict_text = response.content[0].text.strip()
        if not verdict_text:
            raise ValueError("empty verdict text")
    except Exception as e:
        logger.warning(f"⚠️  Adjudicator narrative failed ({e}); using deterministic verdict.")
        verdict_text = _fallback_verdict(m, rec, confidence)

    logger.info(f"✅ Verdict: {_REC_LABEL[rec]} (confidence {confidence:.0%})")
    return verdict_text, rec, confidence
