"""
VerdictFlow — Compliance Agent

Framework: Pydantic AI
Model: Claude Sonnet 4.6

Checks contract against regulatory frameworks (GDPR, SOX, HIPAA, CCPA)
based on contract type and jurisdiction. Identifies non-compliant clauses
with specific remediation steps.
"""

import json
import logging
import os
from typing import Optional

from models.schemas import ComplianceCheck, coerce_compliance_status

logger = logging.getLogger("verdictflow.agents.compliance")


COMPLIANCE_SYSTEM_PROMPT = """You are a regulatory compliance expert specializing in
contract law. Your job is to review a contract and check it against relevant
regulatory frameworks.

Based on the contract type and jurisdiction, check against applicable regulations:
- **GDPR** (EU data protection) — data processing, transfers, DPA requirements
- **CCPA** (California privacy) — consumer data rights, opt-out provisions
- **HIPAA** (healthcare) — PHI handling, BAA requirements
- **SOX** (financial controls) — financial reporting, internal controls
- **PCI DSS** (payment data) — cardholder data protection
- **ADA** (accessibility) — if applicable to services

For each check, provide:
1. **regulation**: Which regulation applies
2. **status**: One of: compliant, non_compliant, needs_review
3. **finding**: What was found (or what's missing)
4. **remediation**: Specific steps to fix non-compliance
5. **relevant_clause**: The clause text relevant to this check

Respond with a JSON array:
[{
    "regulation": "GDPR",
    "status": "non_compliant",
    "finding": "No data processing agreement (DPA) clause found...",
    "remediation": "Add a DPA addendum covering...",
    "relevant_clause": "..."
}]
"""


async def run_compliance_agent(
    contract_text: str,
    doc_type: str = "unknown",
    governing_law: Optional[str] = None,
) -> list[ComplianceCheck]:
    """
    Run the Compliance Agent on a contract.

    Uses contract type and jurisdiction to determine applicable
    regulations, then checks each one.

    Args:
        contract_text: Full contract text
        doc_type: Contract type (NDA, SaaS Agreement, etc.)
        governing_law: Jurisdiction/governing law

    Returns:
        List of ComplianceCheck objects
    """
    logger.info(f"📋 Compliance Agent starting (type={doc_type}, law={governing_law})")

    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        sample = contract_text[:6000]

        context = (
            f"Contract Type: {doc_type}\n"
            f"Governing Law/Jurisdiction: {governing_law or 'Not specified'}\n\n"
            f"Contract Text:\n{sample}"
        )

        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=COMPLIANCE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Check this contract for regulatory compliance:\n\n{context}"
                    ),
                }
            ],
        )

        response_text = response.content[0].text

        # Parse response
        try:
            checks_data = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            checks_data = json.loads(json_match.group()) if json_match else []

        # Convert to ComplianceCheck objects
        checks: list[ComplianceCheck] = []
        for item in checks_data:
            try:
                check = ComplianceCheck(
                    regulation=item.get("regulation", ""),
                    status=coerce_compliance_status(item.get("status")),
                    finding=item.get("finding", ""),
                    remediation=item.get("remediation", ""),
                    relevant_clause=item.get("relevant_clause"),
                )
                checks.append(check)
            except Exception as e:
                logger.warning(f"⚠️  Failed to parse compliance check: {e}")

        logger.info(f"✅ Compliance complete: {len(checks)} checks performed")
        return checks

    except Exception as e:
        logger.error(f"❌ Compliance agent failed: {e}")
        return []
