"""
VerdictFlow — Financial Risk Agent

Framework: LangChain
Model: GPT-4o (optional, falls back to Claude Sonnet 4.6)

Analyzes financial terms — penalty clauses, liability caps, payment schedules,
late fees, auto-renewal costs. Quantifies exposure where possible.
"""

import json
import logging
import os
from typing import Optional

from models.schemas import FinancialRisk

logger = logging.getLogger("verdictflow.agents.financial_risk")


FINANCIAL_RISK_SYSTEM_PROMPT = """You are a financial risk analyst specializing in
contract financial terms. Your job is to identify and quantify all financial risks
in a contract.

Analyze for:
1. **Penalty clauses** — late payment penalties, early termination fees, breach penalties
2. **Liability caps** — total liability limits, per-incident caps, uncapped liability
3. **Payment terms** — payment schedules, net terms, currency risks
4. **Auto-renewal** — automatic renewal terms, price escalation clauses
5. **Insurance requirements** — minimum coverage, additional insured requirements
6. **Indemnification costs** — scope of indemnification, uncapped indemnification
7. **Liquidated damages** — predetermined damage amounts

For each risk found, provide:
1. **category**: One of: penalty, liability_cap, payment_terms, auto_renewal,
   insurance, indemnification, liquidated_damages, other
2. **exposure_amount**: Estimated monetary exposure (null if not quantifiable)
3. **currency**: Currency code (default: USD)
4. **explanation**: Detailed explanation of the financial risk
5. **risk_score**: 0.0 to 1.0 (0 = negligible, 1 = extreme exposure)

Respond with a JSON array:
[{
    "category": "...",
    "exposure_amount": 50000,
    "currency": "USD",
    "explanation": "...",
    "risk_score": 0.7
}]
"""


async def run_financial_risk_agent(
    contract_text: str,
) -> list[FinancialRisk]:
    """
    Run the Financial Risk agent on a contract.

    Tries GPT-4o first (better at numerical analysis), falls back to Claude.

    Args:
        contract_text: Full contract text

    Returns:
        List of FinancialRisk objects
    """
    from core.llm import llm_generate, parse_json_response

    logger.info("💰 Financial Risk Agent starting...")

    try:
        sample = contract_text[:6000]

        response_text = await llm_generate(
            system_prompt=FINANCIAL_RISK_SYSTEM_PROMPT,
            user_prompt=f"Analyze all financial risks in this contract:\n\n{sample}",
            max_tokens=3000,
            temperature=0.2,
        )

        risks_data = parse_json_response(response_text)
        if isinstance(risks_data, dict):
            risks_data = [risks_data]

        return _parse_risks(risks_data)

    except Exception as e:
        logger.error(f"❌ Financial Risk agent failed: {e}")
        return []


def _parse_risks(risks_data: list) -> list[FinancialRisk]:
    """Parse LLM response data into FinancialRisk objects."""
    risks: list[FinancialRisk] = []
    for item in risks_data:
        try:
            risk = FinancialRisk(
                category=item.get("category", "other"),
                exposure_amount=item.get("exposure_amount"),
                currency=item.get("currency", "USD"),
                explanation=item.get("explanation", ""),
                risk_score=min(max(float(item.get("risk_score", 0.5)), 0.0), 1.0),
            )
            risks.append(risk)
        except Exception as e:
            logger.warning(f"⚠️  Failed to parse financial risk: {e}")

    logger.info(f"✅ Financial Risk complete: {len(risks)} risks identified")
    return risks
