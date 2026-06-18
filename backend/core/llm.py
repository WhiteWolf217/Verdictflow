"""
VerdictFlow — LLM Client

Centralised wrapper around the Groq API (OpenAI-compatible).
Every agent calls `llm_generate()` instead of hitting a provider directly.

Includes retry logic and rate-limiting.
"""

import asyncio
import collections
import json
import logging
import os
import re
import time
from typing import Optional

import httpx

logger = logging.getLogger("verdictflow.llm")

# ── Configuration ───────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Fallback to Gemini if GROQ_API_KEY is not set
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = GROQ_MODEL if GROQ_API_KEY else os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
USE_GROQ = bool(GROQ_API_KEY)

# ── Concurrency ─────────────────────────────────────────────────────────────

_semaphore = asyncio.Semaphore(4)  # Max 4 concurrent calls

# ── Global rate limiter ─────────────────────────────────────────────────────

RPM = int(os.getenv("GROQ_RPM", os.getenv("GEMINI_RPM", "28")))


class _RateLimiter:
    """Async sliding-window limiter: at most `rpm` acquisitions per 60s."""

    def __init__(self, rpm: int):
        self.rpm = max(1, rpm)
        self._calls: collections.deque[float] = collections.deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._calls and now - self._calls[0] >= 60.0:
                self._calls.popleft()
            if len(self._calls) >= self.rpm:
                wait = 60.0 - (now - self._calls[0]) + 0.2
                logger.info(f"⏳ Rate limit pacing: waiting {wait:.1f}s (cap {self.rpm}/min)")
                await asyncio.sleep(wait)
                now = time.monotonic()
                while self._calls and now - self._calls[0] >= 60.0:
                    self._calls.popleft()
            self._calls.append(time.monotonic())


_limiter = _RateLimiter(RPM)

# ── Gemini lazy client (fallback) ───────────────────────────────────────────

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        api_key = GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("Neither GROQ_API_KEY nor GEMINI_API_KEY is set.")
        _gemini_client = genai.Client(api_key=api_key)
        logger.info("✅ Gemini client initialised (fallback)")
    return _gemini_client


# ── Public helpers ──────────────────────────────────────────────────────────

MAX_RETRIES = 4
RETRY_DELAYS = [1, 3, 6, 12]  # seconds between retries


async def _groq_generate(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Groq's OpenAI-compatible API."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(GROQ_BASE_URL, json=payload, headers=headers)

    if resp.status_code == 429:
        raise RuntimeError(f"429 RESOURCE_EXHAUSTED: {resp.text}")
    if resp.status_code == 503:
        raise RuntimeError(f"503 UNAVAILABLE: {resp.text}")
    if resp.status_code != 200:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def _gemini_generate(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Google Gemini API."""
    client = _get_gemini_client()
    from google.genai import types

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return response.text or ""


async def llm_generate(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """
    Send a prompt to the LLM and return the text response.

    Uses Groq (Llama 3.3 70B) if GROQ_API_KEY is set, falls back to Gemini.

    Includes:
    - Concurrency limiting (semaphore)
    - Automatic retry with backoff on 503/429 errors
    """
    if not model:
        model = DEFAULT_MODEL

    provider = "groq" if USE_GROQ else "gemini"
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            async with _semaphore:
                if attempt > 0:
                    delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                    logger.info(f"⏳ Retry {attempt + 1}/{MAX_RETRIES} after {delay}s...")
                    await asyncio.sleep(delay)

                await _limiter.acquire()

                if provider == "groq":
                    text = await _groq_generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                else:
                    text = await _gemini_generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

                if not text.strip() and attempt < MAX_RETRIES - 1:
                    logger.warning(
                        f"⚠️  Empty LLM response (attempt {attempt + 1}/{MAX_RETRIES}), retrying..."
                    )
                    continue
                logger.debug(f"LLM response ({provider}/{model}): {text[:120]}...")
                return text

        except Exception as e:
            last_error = e
            error_str = str(e)
            if "503" in error_str or "429" in error_str or "UNAVAILABLE" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                logger.warning(f"⚠️  Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue
            else:
                raise

    raise last_error or RuntimeError("LLM call failed after all retries")


def parse_json_response(text: str) -> list | dict:
    """
    Robustly extract JSON from an LLM response.

    Handles:
    - Pure JSON
    - JSON wrapped in ```json ... ``` code fences
    - JSON embedded in prose
    - Responses that say "no findings" in prose
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

    # 4) Salvage a TRUNCATED JSON array (model hit max_tokens mid-array): take
    #    from the first '[' to the last complete '}' and close the array.
    start = text.find("[")
    if start != -1:
        snippet = text[start:]
        last_obj = snippet.rfind("}")
        if last_obj != -1:
            candidate = snippet[: last_obj + 1] + "]"
            try:
                salvaged = json.loads(candidate)
                if isinstance(salvaged, list) and salvaged:
                    logger.warning(
                        f"Recovered {len(salvaged)} items from a truncated JSON array"
                    )
                    return salvaged
            except json.JSONDecodeError:
                pass

    logger.warning("Failed to parse JSON from LLM response")
    return []
