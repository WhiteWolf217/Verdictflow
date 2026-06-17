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

from models.schemas import ClauseFinding, RiskLevel

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

    Uses RAG to retrieve relevant chunks per category, then analyzes
    each category for risky clauses using Claude.

    Args:
        doc_id: Document ID for Qdrant filtering
        contract_text: Full contract text
        vectorstore: VectorStoreManager for RAG queries

    Returns:
        List of ClauseFinding objects
    """
    logger.info(f"🔍 Clause Analyst starting for doc '{doc_id}'")

    all_findings: list[ClauseFinding] = []

    # For each clause category, use RAG to find relevant sections
    for category in CLAUSE_CATEGORIES:
        logger.info(f"  📂 Analyzing category: {category}")

        # Build context from RAG or full text
        context = ""
        if vectorstore:
            # Semantic search for clauses related to this category
            search_query = f"{category} clause terms conditions obligations"
            results = vectorstore.search(
                query=search_query,
                doc_id=doc_id,
                top_k=5,
            )
            if results:
                context = "\n\n---\n\n".join([r["text"] for r in results])
            else:
                # Fall back to a portion of the full text
                context = contract_text[:6000]
        else:
            context = contract_text[:6000]

        if not context.strip():
            continue

        # Analyze with Claude
        findings = await _analyze_category(category, context)
        all_findings.extend(findings)

    logger.info(f"✅ Clause Analyst complete: {len(all_findings)} findings")
    return all_findings


async def _analyze_category(
    category: str,
    context: str,
) -> list[ClauseFinding]:
    """Analyze contract text for risky clauses in a specific category."""
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=CLAUSE_ANALYST_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Analyze the following contract text for risky '{category}' clauses.\n\n"
                        f"Contract text:\n{context}"
                    ),
                }
            ],
        )

        response_text = response.content[0].text

        # Parse JSON response
        try:
            findings_data = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                findings_data = json.loads(json_match.group())
            else:
                findings_data = []

        # Convert to ClauseFinding objects
        findings = []
        for item in findings_data:
            try:
                finding = ClauseFinding(
                    clause_text=item.get("clause_text", ""),
                    category=item.get("category", category),
                    risk_level=RiskLevel(item.get("risk_level", "medium")),
                    explanation=item.get("explanation", ""),
                    recommendations=item.get("recommendations", []),
                )
                findings.append(finding)
            except Exception as e:
                logger.warning(f"⚠️  Failed to parse finding: {e}")

        return findings

    except Exception as e:
        logger.error(f"❌ Clause analysis failed for '{category}': {e}")
        return []
