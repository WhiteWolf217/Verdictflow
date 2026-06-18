"""
VerdictFlow — Redline Agent

Framework: Direct Anthropic API (Claude Sonnet 4.6)
Model: Claude Sonnet 4.6

Synthesizes findings from all prior agents. Generates specific
redline edits (original → suggested text) with rationale.
Prioritizes edits as required/recommended/optional.
"""

import json
import logging
import os
from typing import Optional

from models.schemas import (
    ClauseFinding,
    ComplianceCheck,
    EditPriority,
    FinancialRisk,
    RedlineEdit,
    RedTeamAttack,
    coerce_edit_priority,
)

logger = logging.getLogger("verdictflow.agents.redline")


REDLINE_SYSTEM_PROMPT = """You are an expert contract redlining specialist. You have been given
the findings from a team of specialized contract review agents. Your job is to generate
specific, actionable redline edits to improve the contract.

For each edit, provide:
1. **original_text**: The exact original contract text to be changed
2. **suggested_text**: The proposed replacement text
3. **rationale**: Why this change is needed (reference specific findings)
4. **priority**: One of:
   - "required" — Must be changed (addresses critical risks or non-compliance)
   - "recommended" — Should be changed (addresses high/medium risks)
   - "optional" — Nice to have (improves clarity or adds protections)

Guidelines:
- Make edits specific and actionable — don't be vague
- Preserve legal language style and tone
- Address the most critical findings first
- Group related edits when they affect the same clause
- Ensure suggested text is legally sound and balanced

Respond with a JSON array:
[{
    "original_text": "...",
    "suggested_text": "...",
    "rationale": "...",
    "priority": "required"
}]
"""


async def run_redline_agent(
    contract_text: str,
    clause_findings: list[ClauseFinding],
    red_team_attacks: list[RedTeamAttack],
    financial_risks: list[FinancialRisk],
    compliance_checks: list[ComplianceCheck],
) -> list[RedlineEdit]:
    """
    Run the Redline Agent to generate contract edit suggestions.

    Synthesizes findings from all prior agents to produce
    specific redline edits with priority rankings.

    Args:
        contract_text: Full contract text
        clause_findings: From the Clause Analyst
        red_team_attacks: From the Red Team
        financial_risks: From the Financial Risk agent
        compliance_checks: From the Compliance agent

    Returns:
        List of RedlineEdit objects
    """
    logger.info("✏️  Redline Agent starting...")

    # Build findings summary for the redline agent
    findings_summary = _build_findings_summary(
        clause_findings, red_team_attacks, financial_risks, compliance_checks
    )

    try:
        from core.llm import llm_generate, parse_json_response

        sample = contract_text[:5000]

        response_text = await llm_generate(
            system_prompt=REDLINE_SYSTEM_PROMPT,
            user_prompt=(
                f"Generate redline edits for this contract based on the following findings.\n\n"
                f"=== FINDINGS FROM REVIEW AGENTS ===\n{findings_summary}\n\n"
                f"=== CONTRACT TEXT ===\n{sample}"
            ),
            max_tokens=4096,
        )

        edits_data = parse_json_response(response_text)
        if isinstance(edits_data, dict):
            edits_data = [edits_data]

        # Convert to RedlineEdit objects
        edits: list[RedlineEdit] = []
        for item in edits_data:
            try:
                edit = RedlineEdit(
                    original_text=item.get("original_text", ""),
                    suggested_text=item.get("suggested_text", ""),
                    rationale=item.get("rationale", ""),
                    priority=coerce_edit_priority(item.get("priority")),
                )
                edits.append(edit)
            except Exception as e:
                logger.warning(f"⚠️  Failed to parse redline edit: {e}")

        # Sort by priority: required > recommended > optional
        priority_order = {"required": 0, "recommended": 1, "optional": 2}
        edits.sort(key=lambda e: priority_order.get(e.priority.value, 99))

        logger.info(f"✅ Redline complete: {len(edits)} edits generated")
        return edits

    except Exception as e:
        logger.error(f"❌ Redline agent failed: {e}")
        return []


def _build_findings_summary(
    clause_findings: list[ClauseFinding],
    red_team_attacks: list[RedTeamAttack],
    financial_risks: list[FinancialRisk],
    compliance_checks: list[ComplianceCheck],
) -> str:
    """Build a structured text summary of all findings for the redline agent."""
    parts: list[str] = []

    # Clause findings (focus on high/critical)
    high_clauses = [f for f in clause_findings if f.risk_level.value in ("high", "critical")]
    if high_clauses:
        parts.append("## CLAUSE ANALYSIS (High/Critical)")
        for f in high_clauses:
            parts.append(
                f"- [{f.risk_level.value.upper()}] {f.category}: {f.explanation}\n"
                f"  Clause: \"{f.clause_text[:200]}\"\n"
                f"  Recommendations: {', '.join(f.recommendations)}"
            )

    # Red team attacks
    if red_team_attacks:
        parts.append("\n## RED TEAM ATTACKS")
        for a in red_team_attacks:
            parts.append(
                f"- [{a.severity.value.upper()}] {a.attack_vector}: {a.exploit_scenario[:200]}\n"
                f"  Target: \"{a.target_clause[:200]}\""
            )

    # Financial risks
    high_financial = [r for r in financial_risks if r.risk_score >= 0.5]
    if high_financial:
        parts.append("\n## FINANCIAL RISKS (Score >= 0.5)")
        for r in high_financial:
            exposure = f"${r.exposure_amount:,.0f} {r.currency}" if r.exposure_amount else "Unquantified"
            parts.append(
                f"- [{r.category}] Exposure: {exposure} (Score: {r.risk_score:.1f})\n"
                f"  {r.explanation}"
            )

    # Compliance checks (non-compliant only)
    non_compliant = [c for c in compliance_checks if c.status.value == "non_compliant"]
    if non_compliant:
        parts.append("\n## COMPLIANCE FAILURES")
        for c in non_compliant:
            parts.append(
                f"- [{c.regulation}] NON-COMPLIANT: {c.finding}\n"
                f"  Remediation: {c.remediation}"
            )

    return "\n".join(parts) if parts else "No significant findings reported."
