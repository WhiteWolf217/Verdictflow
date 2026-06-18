"""
VerdictFlow — LLM Client

Centralised wrapper around the Google Gemini API.
Every agent calls `llm_generate()` instead of hitting a provider directly.

Includes retry logic and rate-limiting for free-tier Gemini accounts.
"""

import asyncio
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger("verdictflow.llm")

# ── Lazy-init client ────────────────────────────────────────────────────────

_client = None
_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent Gemini calls


def _get_client():
    global _client
    if _client is None:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com/apikey"
            )
        _client = genai.Client(api_key=api_key)
        logger.info("✅ Gemini client initialised")
    return _client


# ── Public helpers ──────────────────────────────────────────────────────────

DEFAULT_MODEL = "gemini-2.5-flash"

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]  # seconds between retries


async def llm_generate(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """
    Send a prompt to Gemini and return the text response.

    Includes:
    - Concurrency limiting (semaphore) to avoid overwhelming free tier
    - Automatic retry with backoff on 503/429 errors

    Args:
        system_prompt: System-level instructions for the model.
        user_prompt: The user message / task.
        model: Gemini model name (default gemini-2.5-flash).
        max_tokens: Maximum output tokens.
        temperature: Sampling temperature.

    Returns:
        The model's text response.
    """
    client = _get_client()
    from google.genai import types

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            async with _semaphore:
                # Add small stagger to avoid burst
                if attempt > 0:
                    delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                    logger.info(f"⏳ Retry {attempt + 1}/{MAX_RETRIES} after {delay}s...")
                    await asyncio.sleep(delay)

                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                    ),
                )

                text = response.text or ""
                logger.debug(f"LLM response ({model}): {text[:120]}...")
                return text

        except Exception as e:
            last_error = e
            error_str = str(e)
            # Retry on rate limit and service unavailable errors
            if "503" in error_str or "429" in error_str or "UNAVAILABLE" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                logger.warning(f"⚠️  Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue
            else:
                raise  # Non-retryable error

    # All retries exhausted
    raise last_error or RuntimeError("LLM call failed after all retries")


def parse_json_response(text: str) -> list | dict:
    """
    Robustly extract JSON from an LLM response.

    Handles:
    - Pure JSON
    - JSON wrapped in ```json ... ``` code fences
    - JSON embedded in prose
    - Gemini responses that say "no findings" in prose
    """
    text = text.strip()

    # Quick check: if the response is clearly "nothing found" prose, return empty
    nothing_phrases = [
        "no risky clauses", "no findings", "no issues", "no vulnerabilities",
        "no risks identified", "no financial risks", "no compliance issues",
        "does not contain", "not applicable",
    ]
    text_lower = text.lower()
    if any(phrase in text_lower for phrase in nothing_phrases) and "[" not in text:
        return []

    # 1) Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) Try code-fence extraction
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3) Try to find an array or object
    for pattern in (r"\[.*\]", r"\{.*\}"):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                continue

    logger.warning("Failed to parse JSON from LLM response")
    return []
