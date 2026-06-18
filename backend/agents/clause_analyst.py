"""
VerdictFlow — Clause Analyst Agent

Framework: LangChain + RAG (Qdrant retrieval)
Model: Claude Sonnet 4.6

Performs clause-by-clause analysis using RAG. Identifies risky clauses
across categories: liability, indemnification, termination, IP assignment,
non-compete, confidentiality, force majeure.
"""

import json
import logging
import os
from typing import Optional

from models.schemas import ClauseFinding, RiskLevel, coerce_risk_level

logger = logging.getLogger("verdictflow.agents.clause_analyst")


# ── Analysis Categories ──────────────────────────────────────────────────────

CLAUSE_CATEGORIES = [
    "liability",
    "indemnification",
    "termination",
    "intellectual_property",
    "non_compete",
    "confidentiality",
    "force_majeure",
    "limitation_of_liability",
    "warranty",
    "dispute_resolution",
    "data_protection",
    "assignment",
]

CLAUSE_ANALYST_SYSTEM_PROMPT = """You are an expert contract clause analyst. Your role is to
review contract text and identify potentially risky, unusual, or problematic clauses.

For each risky clause you find, provide:
1. **clause_text**: The exact text of the clause (or relevant excerpt)
2. **category**: One of: liability, indemnification, termination, intellectual_property,
   non_compete, confidentiality, force_majeure, limitation_of_liability, warranty,
   dispute_resolution, data_protection, assignment
3. **risk_level**: One of: low, medium, high, critical
4. **explanation**: Why this clause is risky and what the implications are
5. **recommendations**: A list of specific recommendations to mitigate the risk

Focus on:
- One-sided or overly broad clauses
- Missing standard protections
- Unusual penalty or liability terms
- Vague language that could be exploited
- Clauses that deviate from industry norms

When a MARKET-STANDARD REFERENCE clause is provided, compare the contract text
against it and explicitly call out how (and how far) the contract deviates from
that market standard in your explanation.

Respond with a JSON array of findings:
[
    {
        "clause_text": "...",
        "category": "...",
        "risk_level": "...",
        "explanation": "...",
        "recommendations": ["...", "..."]
    }
]

If no risky clauses are found in the provided text, return an empty array: []
"""


async def run_clause_analyst(
    doc_id: str,
    contract_text: str,
    vectorstore=None,
) -> list[ClauseFinding]:
    """
    Run the Clause Analyst agent on a contract.

    Analyzes ALL clause categories in a SINGLE LLM call (the full contract is
    passed in context, grounded against the market-standard precedent library).
    This replaced a 12-call-per-contract fan-out that exhausted free-tier LLM
    rate limits; one call is faster, cheaper, and lets the model reason across
    categories holistically. Findings are de-duplicated before returning.

    Args:
        doc_id: Document ID for Qdrant filtering
        contract_text: Full contract text
        vectorstore: VectorStoreManager for precedent queries

    Returns:
        De-duplicated list of ClauseFinding objects
    """
    logger.info(f"🔍 Clause Analyst starting for doc '{doc_id}' ({len(CLAUSE_CATEGORIES)} categories, single pass)")

    context = (contract_text or "").strip()
    if not context:
        return []
    context = context[:14000]  # keep prompt within budget for typical contracts

    # Pull a compact set of market-standard precedents for grounded comparison.
    reference_block = ""
    if vectorstore and hasattr(vectorstore, "search_precedents"):
        precedent_lines = []
        for cat in CLAUSE_CATEGORIES:
            hits = vectorstore.search_precedents(query=f"{cat} standard clause", top_k=1)
            if hits and hits[0].get("risk_notes"):
                precedent_lines.append(f"- {cat}: {hits[0]['risk_notes']}")
        if precedent_lines:
            reference_block = (
                "\n\nMARKET-STANDARD RED FLAGS (use these to judge deviation):\n"
                + "\n".join(precedent_lines[:12])
            )

    all_findings = await _analyze_all_categories(context, reference_block)

    deduped = _dedupe_findings(all_findings)
    logger.info(
        f"✅ Clause Analyst complete: {len(deduped)} findings "
        f"({len(all_findings) - len(deduped)} duplicates removed)"
    )
    return deduped


def _dedupe_findings(findings: list[ClauseFinding]) -> list[ClauseFinding]:
    """Drop near-duplicate findings keyed by (category, first 80 chars of clause)."""
    seen: set[tuple[str, str]] = set()
    out: list[ClauseFinding] = []
    for f in findings:
        key = (f.category, " ".join(f.clause_text.lower().split())[:80])
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


async def _analyze_all_categories(
    context: str,
    reference_block: str = "",
) -> list[ClauseFinding]:
    """Analyze the full contract across ALL clause categories in one LLM call."""
    from core.llm import llm_generate, parse_json_response

    categories_list = ", ".join(CLAUSE_CATEGORIES)

    try:
        response_text = await llm_generate(
            system_prompt=CLAUSE_ANALYST_SYSTEM_PROMPT,
            user_prompt=(
                "Analyze the ENTIRE contract below and identify every risky, unusual, "
                "or one-sided clause. Cover all of these categories where applicable: "
                f"{categories_list}. Return one finding per distinct risky clause, each "
                "tagged with its category."
                f"{reference_block}\n\n"
                f"Contract text:\n{context}"
            ),
            max_tokens=4096,
            temperature=0.1,
        )

        findings_data = parse_json_response(response_text)
        if isinstance(findings_data, dict):
            findings_data = [findings_data]

        findings = []
        for item in findings_data:
            if not isinstance(item, dict):
                continue
            try:
                findings.append(ClauseFinding(
                    clause_text=item.get("clause_text", ""),
                    category=item.get("category", "general"),
                    risk_level=coerce_risk_level(item.get("risk_level")),
                    explanation=item.get("explanation", ""),
                    recommendations=item.get("recommendations", []),
                ))
            except Exception as e:
                logger.warning(f"⚠️  Failed to parse finding: {e}")

        return findings

    except Exception as e:
        logger.error(f"❌ Clause analysis failed: {e}")
        return []
