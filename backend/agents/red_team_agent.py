"""
VerdictFlow — Red Team Agent

Framework: CrewAI (2-agent crew: Attacker + Defender)
Model: Featherless AI (open-source, e.g., Qwen/Qwen2.5-72B-Instruct)

Red-teams the contract by identifying ambiguities, missing clauses,
conflicting terms, and exploitable loopholes. Uses an adversarial
Attacker/Defender pattern for validated findings.
"""

import json
import logging
import os
from typing import Optional

from models.schemas import RedTeamAttack, RiskLevel

logger = logging.getLogger("verdictflow.agents.red_team")


# ── Prompts ──────────────────────────────────────────────────────────────────

ATTACKER_SYSTEM_PROMPT = """You are a ruthless contract exploitation specialist.
Your goal is to find every vulnerability, ambiguity, missing clause, conflicting term,
and exploitable loophole in the contract.

Think like an adversarial party who wants to:
- Exploit vague language for maximum advantage
- Identify missing protections that leave one party exposed
- Find contradictions between different clauses
- Discover escape clauses or termination loopholes
- Identify financial risks through creative interpretation

For each vulnerability found, provide:
1. **attack_vector**: One of: ambiguity, missing_clause, conflict, loophole, vague_language, unfair_term
2. **target_clause**: The specific clause text being attacked
3. **exploit_scenario**: A detailed, realistic scenario of how this could be exploited
4. **severity**: One of: low, medium, high, critical

Respond with a JSON array:
[{"attack_vector": "...", "target_clause": "...", "exploit_scenario": "...", "severity": "..."}]
"""

DEFENDER_SYSTEM_PROMPT = """You are a contract defense specialist. You are reviewing
adversarial attacks found against a contract. Your job is to:

1. Validate each attack — determine if it represents a real, exploitable vulnerability
2. Filter out false positives — attacks that are unlikely or based on misinterpretation
3. Assess true severity — some attacks may be theoretical but impractical

For each attack, provide your assessment:
- **is_valid**: true/false — is this a real vulnerability?
- **adjusted_severity**: What should the severity actually be? (low/medium/high/critical)
- **defender_assessment**: Brief explanation of your validation

Respond with a JSON array matching the input attacks:
[{"attack_index": 0, "is_valid": true, "adjusted_severity": "high", "defender_assessment": "..."}]
"""


async def run_red_team_agent(
    contract_text: str,
) -> list[RedTeamAttack]:
    """
    Run the Red Team agent using an Attacker/Defender pattern.

    Step 1: Attacker identifies vulnerabilities
    Step 2: Defender validates and filters false positives

    Args:
        contract_text: Full contract text

    Returns:
        List of validated RedTeamAttack objects
    """
    logger.info("🔴 Red Team Agent starting...")

    # Step 1: Run the Attacker
    raw_attacks = await _run_attacker(contract_text)
    logger.info(f"⚔️  Attacker found {len(raw_attacks)} potential vulnerabilities")

    if not raw_attacks:
        return []

    # Step 2: Run the Defender to validate
    validated_attacks = await _run_defender(raw_attacks, contract_text)
    logger.info(f"🛡️  Defender validated {len(validated_attacks)} attacks")

    return validated_attacks


async def _run_attacker(contract_text: str) -> list[dict]:
    """Run the Attacker agent to find vulnerabilities."""
    # Use first ~6000 chars for analysis
    sample = contract_text[:6000]

    try:
        # Use Featherless AI (OpenAI-compatible endpoint)
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url="https://api.featherless.ai/v1",
            api_key=os.getenv("FEATHERLESS_API_KEY", ""),
        )

        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[
                {"role": "system", "content": ATTACKER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Find all vulnerabilities in this contract:\n\n{sample}",
                },
            ],
            max_tokens=3000,
            temperature=0.7,  # Slightly creative for finding edge cases
        )

        response_text = response.choices[0].message.content

        # Parse JSON
        try:
            attacks = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                attacks = json.loads(json_match.group())
            else:
                attacks = []

        return attacks

    except Exception as e:
        logger.error(f"❌ Attacker agent failed: {e}")
        # Fallback: try with Anthropic
        return await _run_attacker_fallback(sample)


async def _run_attacker_fallback(contract_text: str) -> list[dict]:
    """Fallback attacker using Claude if Featherless is unavailable."""
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            system=ATTACKER_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Find all vulnerabilities in this contract:\n\n{contract_text}",
                }
            ],
        )

        response_text = response.content[0].text
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            return json.loads(json_match.group()) if json_match else []

    except Exception as e:
        logger.error(f"❌ Attacker fallback also failed: {e}")
        return []


async def _run_defender(attacks: list[dict], contract_text: str) -> list[RedTeamAttack]:
    """Run the Defender agent to validate attacks."""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url="https://api.featherless.ai/v1",
            api_key=os.getenv("FEATHERLESS_API_KEY", ""),
        )

        attacks_json = json.dumps(attacks, indent=2)

        response = await client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[
                {"role": "system", "content": DEFENDER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Validate these attacks against the contract:\n\n"
                        f"Attacks:\n{attacks_json}\n\n"
                        f"Contract (excerpt):\n{contract_text[:3000]}"
                    ),
                },
            ],
            max_tokens=2000,
            temperature=0.3,  # Conservative for validation
        )

        response_text = response.choices[0].message.content

        # Parse defender assessments
        try:
            assessments = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            assessments = json.loads(json_match.group()) if json_match else []

        # Build validated attacks
        validated: list[RedTeamAttack] = []
        assessment_map = {a.get("attack_index", i): a for i, a in enumerate(assessments)}

        for i, attack in enumerate(attacks):
            assessment = assessment_map.get(i, {})
            is_valid = assessment.get("is_valid", True)

            if not is_valid:
                continue

            severity = assessment.get("adjusted_severity", attack.get("severity", "medium"))

            validated.append(RedTeamAttack(
                attack_vector=attack.get("attack_vector", "unknown"),
                target_clause=attack.get("target_clause", ""),
                exploit_scenario=attack.get("exploit_scenario", ""),
                severity=RiskLevel(severity),
                defender_assessment=assessment.get("defender_assessment"),
            ))

        return validated

    except Exception as e:
        logger.error(f"❌ Defender agent failed: {e}")
        # Return all attacks unvalidated
        return [
            RedTeamAttack(
                attack_vector=a.get("attack_vector", "unknown"),
                target_clause=a.get("target_clause", ""),
                exploit_scenario=a.get("exploit_scenario", ""),
                severity=RiskLevel(a.get("severity", "medium")),
            )
            for a in attacks
        ]
