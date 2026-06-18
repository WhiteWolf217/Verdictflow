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

    For each clause category, uses RAG to retrieve the relevant contract
    sections AND the closest market-standard precedent clause, then analyzes
    the category with Claude. All categories run concurrently for speed.
    Findings are de-duplicated before returning.

    Args:
        doc_id: Document ID for Qdrant filtering
        contract_text: Full contract text
        vectorstore: VectorStoreManager for RAG + precedent queries

    Returns:
        De-duplicated list of ClauseFinding objects
    """
    import asyncio

    logger.info(f"🔍 Clause Analyst starting for doc '{doc_id}' ({len(CLAUSE_CATEGORIES)} categories)")

    async def analyze_one(category: str) -> list[ClauseFinding]:
        # Contract context for this category (RAG over the uploaded doc).
        context = ""
        if vectorstore:
            results = vectorstore.search(
                query=f"{category} clause terms conditions obligations",
                doc_id=doc_id,
                top_k=5,
            )
            context = "\n\n---\n\n".join(r["text"] for r in results) if results else ""
        if not context.strip():
            context = contract_text[:6000]
        if not context.strip():
            return []

        # Closest market-standard precedent for grounded comparison.
        precedent = None
        if vectorstore and hasattr(vectorstore, "search_precedents"):
            hits = vectorstore.search_precedents(
                query=f"{category} standard clause", top_k=1
            )
            if hits:
                precedent = hits[0]

        return await _analyze_category(category, context, precedent)

    results = await asyncio.gather(
        *(analyze_one(c) for c in CLAUSE_CATEGORIES),
        return_exceptions=True,
    )

    all_findings: list[ClauseFinding] = []
    for category, res in zip(CLAUSE_CATEGORIES, results):
        if isinstance(res, Exception):
            logger.error(f"❌ Clause analysis failed for '{category}': {res}")
            continue
        all_findings.extend(res)

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


async def _analyze_category(
    category: str,
    context: str,
    precedent: Optional[dict] = None,
) -> list[ClauseFinding]:
    """Analyze contract text for risky clauses in a specific category."""
    from core.llm import llm_generate, parse_json_response

    try:
        reference_block = ""
        if precedent:
            reference_block = (
                "\n\nMARKET-STANDARD REFERENCE (for comparison):\n"
                f"Standard clause: {precedent.get('standard_text', '')}\n"
                f"What makes a variant risky: {precedent.get('risk_notes', '')}\n"
            )

        response_text = await llm_generate(
            system_prompt=CLAUSE_ANALYST_SYSTEM_PROMPT,
            user_prompt=(
                f"Analyze the following contract text for risky '{category}' clauses."
                f"{reference_block}\n\n"
                f"Contract text:\n{context}"
            ),
            max_tokens=2048,
            temperature=0.1,
        )

        findings_data = parse_json_response(response_text)
        if isinstance(findings_data, dict):
            findings_data = [findings_data]

        findings = []
        for item in findings_data:
            try:
                findings.append(ClauseFinding(
                    clause_text=item.get("clause_text", ""),
                    category=item.get("category", category),
                    risk_level=coerce_risk_level(item.get("risk_level")),
                    explanation=item.get("explanation", ""),
                    recommendations=item.get("recommendations", []),
                ))
            except Exception as e:
                logger.warning(f"⚠️  Failed to parse finding: {e}")

        return findings

    except Exception as e:
        logger.error(f"❌ Clause analysis failed for '{category}': {e}")
        return []
