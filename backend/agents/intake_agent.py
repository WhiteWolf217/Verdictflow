"""
VerdictFlow — Intake Agent

Framework: Pydantic AI
Model: Claude Sonnet 4.6 (Anthropic API)

Receives an uploaded contract, parses it, chunks it, indexes into Qdrant,
classifies document type, and extracts key metadata (parties, dates, law).
"""

import logging
import os
from typing import Optional

from models.schemas import ContractMetadata
from core.parser import ParsedDocument, parse_contract
from core.chunker import chunk_document

logger = logging.getLogger("verdictflow.agents.intake")


# ── Intake Agent System Prompt ───────────────────────────────────────────────

INTAKE_SYSTEM_PROMPT = """You are a contract intake specialist. Your job is to analyze
a contract document and extract structured metadata.

Given the full text of a contract, you must identify:
1. **Document Type**: Classify as one of: NDA, SaaS Agreement, Employment Contract,
   Service Agreement, License Agreement, Partnership Agreement, Lease Agreement, or Other.
2. **Parties**: List all parties named in the contract.
3. **Effective Date**: The date the contract becomes effective (if stated).
4. **Governing Law**: The jurisdiction/governing law specified (if stated).
5. **Key Terms Summary**: A 2-3 sentence summary of the contract's primary purpose and terms.

Respond in JSON format with these exact keys:
{
    "doc_type": "...",
    "parties": ["Party A", "Party B"],
    "effective_date": "YYYY-MM-DD or null",
    "governing_law": "...",
    "key_terms_summary": "..."
}
"""


async def run_intake_agent(
    file_path: str,
    filename: str,
    vectorstore=None,
) -> tuple[ContractMetadata, ParsedDocument, list]:
    """
    Run the Intake Agent on an uploaded contract.

    Steps:
    1. Parse the document (PDF/DOCX → structured text)
    2. Chunk the text for vector indexing
    3. Index chunks into Qdrant
    4. Use Claude to classify and extract metadata

    Args:
        file_path: Path to the uploaded contract file
        filename: Original filename
        vectorstore: VectorStoreManager instance

    Returns:
        Tuple of (ContractMetadata, ParsedDocument, chunks)
    """
    logger.info(f"🚀 Intake Agent starting for '{filename}'")

    # Step 1: Parse the document
    parsed_doc = parse_contract(file_path, filename)
    logger.info(f"📄 Parsed: {parsed_doc.page_count} pages, {parsed_doc.total_chars} chars")

    # Step 2: Chunk the document
    chunks = chunk_document(parsed_doc)
    logger.info(f"📦 Chunked: {len(chunks)} chunks")

    # Step 3: Index into Qdrant
    if vectorstore:
        vectorstore.index_document(parsed_doc.doc_id, chunks)
        logger.info(f"📥 Indexed {len(chunks)} chunks into Qdrant")

    # Step 4: Classify and extract metadata using Claude
    metadata = await _classify_contract(parsed_doc)

    logger.info(
        f"✅ Intake complete: type={metadata.doc_type}, "
        f"parties={metadata.parties}, law={metadata.governing_law}"
    )

    return metadata, parsed_doc, chunks


async def _classify_contract(parsed_doc: ParsedDocument) -> ContractMetadata:
    """
    Use Claude Sonnet to classify the contract and extract metadata.

    Uses Pydantic AI pattern with Anthropic client for structured output.
    """
    # Take first ~4000 chars for classification (enough for most contracts)
    sample_text = parsed_doc.raw_text[:4000]

    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=INTAKE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Analyze this contract and extract metadata:\n\n{sample_text}",
                }
            ],
        )

        # Parse Claude's JSON response
        import json
        response_text = response.content[0].text
        # Try to extract JSON from the response
        try:
            classified = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON block in markdown
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                classified = json.loads(json_match.group())
            else:
                classified = {}

        metadata = ContractMetadata(
            doc_id=parsed_doc.doc_id,
            filename=parsed_doc.filename,
            page_count=parsed_doc.page_count,
            total_chars=parsed_doc.total_chars,
            doc_type=classified.get("doc_type", "unknown"),
            parties=classified.get("parties", []),
            effective_date=classified.get("effective_date"),
            governing_law=classified.get("governing_law"),
            key_terms_summary=classified.get("key_terms_summary"),
        )

        return metadata

    except Exception as e:
        logger.warning(f"⚠️  Claude classification failed: {e}. Using defaults.")
        return ContractMetadata(
            doc_id=parsed_doc.doc_id,
            filename=parsed_doc.filename,
            page_count=parsed_doc.page_count,
            total_chars=parsed_doc.total_chars,
            doc_type="unknown",
        )
