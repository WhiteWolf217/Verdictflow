"""
VerdictFlow — Contract Version Comparison API

Upload v1 and v2 of a contract; agents analyse both and report:
- What clauses changed
- New risks introduced
- Risks removed / mitigated
- Overall risk delta (↑ / ↓ / →)
"""

import asyncio
import json
import logging
import os
import tempfile
import uuid

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from core.llm import llm_generate, parse_json_response
from core.parser import parse_contract

logger = logging.getLogger("verdictflow.compare")
router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _save_upload(file: UploadFile) -> str:
    """Save uploaded file and return path."""
    ext = os.path.splitext(file.filename or "doc")[1] or ".txt"
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex[:8]}{ext}")
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return path


async def _extract_text(path: str, filename: str) -> str:
    """Parse document and return full text."""
    parsed = await asyncio.to_thread(parse_contract, path, filename)
    return parsed.full_text


@router.post("/api/contracts/compare")
async def compare_versions(
    v1: UploadFile = File(...),
    v2: UploadFile = File(...),
):
    """Compare two versions of a contract and return risk delta analysis."""
    logger.info(f"📊 Comparing: '{v1.filename}' (v1) vs '{v2.filename}' (v2)")

    # Save and parse both files
    path1 = await _save_upload(v1)
    path2 = await _save_upload(v2)

    try:
        text1, text2 = await asyncio.gather(
            _extract_text(path1, v1.filename or "v1"),
            _extract_text(path2, v2.filename or "v2"),
        )
    except Exception as e:
        raise HTTPException(400, f"Failed to parse documents: {e}")
    finally:
        # Clean up uploaded files
        for p in [path1, path2]:
            try:
                os.remove(p)
            except OSError:
                pass

    # Truncate to fit in context window
    max_chars = 6000
    text1_trunc = text1[:max_chars]
    text2_trunc = text2[:max_chars]

    # Run comparison via LLM
    system_prompt = """You are a senior contract analyst comparing two versions of the same contract.
Identify ALL meaningful changes between v1 and v2 and assess how each change affects risk.

Return a JSON object with:
{
  "overall_risk_delta": "increased" | "decreased" | "unchanged",
  "overall_summary": "2-3 sentence summary of the most important changes",
  "risk_score_v1": <number 0-100>,
  "risk_score_v2": <number 0-100>,
  "changes": [
    {
      "clause_area": "e.g. Liability, Termination, Indemnification",
      "change_type": "added" | "removed" | "modified",
      "v1_text": "relevant text from v1 (or null if added)",
      "v2_text": "relevant text from v2 (or null if removed)",
      "risk_impact": "increased" | "decreased" | "neutral",
      "severity": "low" | "medium" | "high" | "critical",
      "explanation": "1-2 sentence explanation of the change and its risk impact"
    }
  ],
  "new_risks": ["list of new risks introduced in v2"],
  "mitigated_risks": ["list of risks from v1 that were fixed or reduced in v2"],
  "recommendation": "1-2 sentence recommendation for the reviewing party"
}

Return ONLY valid JSON, no markdown fences."""

    user_prompt = f"""Compare these two contract versions:

=== VERSION 1 (Original) ===
{text1_trunc}

=== VERSION 2 (Revised) ===
{text2_trunc}

Analyse all changes and their risk impact."""

    try:
        raw = await llm_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096,
            temperature=0.2,
        )

        # Parse JSON response
        result = parse_json_response(raw)
        if isinstance(result, list):
            # Shouldn't be a list, wrap it
            result = {"changes": result, "overall_risk_delta": "unchanged", "overall_summary": "Analysis complete."}

        # Ensure required fields
        result.setdefault("overall_risk_delta", "unchanged")
        result.setdefault("overall_summary", "")
        result.setdefault("risk_score_v1", 50)
        result.setdefault("risk_score_v2", 50)
        result.setdefault("changes", [])
        result.setdefault("new_risks", [])
        result.setdefault("mitigated_risks", [])
        result.setdefault("recommendation", "")

        # Add metadata
        result["v1_filename"] = v1.filename
        result["v2_filename"] = v2.filename
        result["v1_char_count"] = len(text1)
        result["v2_char_count"] = len(text2)

        logger.info(f"✅ Comparison complete: {len(result['changes'])} changes, delta={result['overall_risk_delta']}")
        return result

    except Exception as e:
        logger.error(f"❌ Comparison LLM failed: {e}")
        raise HTTPException(500, f"Analysis failed: {e}")
