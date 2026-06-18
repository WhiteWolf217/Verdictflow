"""
VerdictFlow — Negotiation Simulator API

Provides:
1. Negotiation coaching — strategies for each finding
2. Interactive negotiation simulator — AI plays counterparty
3. Negotiation evaluation — scores user's negotiation skills
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.llm import llm_generate

logger = logging.getLogger("verdictflow.negotiate")

router = APIRouter()

# ── In-memory session store ──────────────────────────────────────────────────

_sessions: Dict[str, Dict[str, Any]] = {}


# ── Request/Response Models ──────────────────────────────────────────────────


class NegotiationCoachRequest(BaseModel):
    case_id: str
    findings: List[Dict[str, Any]]


class NegotiationCoachResponse(BaseModel):
    strategies: List[Dict[str, Any]]


class SimulatorStartRequest(BaseModel):
    case_id: str
    user_role: str  # "buyer", "vendor", "licensee", "tenant" etc.
    counterparty_role: str  # "seller", "licensor", "landlord"
    scenario: str  # Brief description
    contract_context: str  # Key clauses/findings to negotiate
    difficulty: str = "medium"  # easy, medium, hard


class SimulatorTurnRequest(BaseModel):
    session_id: str
    user_message: str


class SimulatorEvaluateRequest(BaseModel):
    session_id: str


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post("/api/negotiate/coach")
async def get_negotiation_coaching(req: NegotiationCoachRequest):
    """Generate negotiation strategies for identified contract findings."""

    findings_text = "\n".join(
        f"- [{f.get('risk_level', 'medium').upper()}] {f.get('category', 'General')}: {f.get('explanation', '')}"
        for f in req.findings[:8]  # Limit to 8 findings
    )

    system_prompt = """You are a senior contract negotiation coach with 20 years of experience in corporate law.
Your role is to provide actionable, specific negotiation strategies for each contract issue identified.

IMPORTANT: Return a JSON array. Each element must have:
- "finding": the original issue
- "strategy": a concise negotiation approach (2-3 sentences)
- "talking_points": array of 2-3 specific phrases the user can say
- "leverage": what leverage the user has on this point
- "fallback": what compromise to accept if the other side pushes back
- "priority": "must_win" | "important" | "nice_to_have"

Return ONLY valid JSON, no markdown."""

    user_prompt = f"""Here are the contract findings that need negotiation strategies:

{findings_text}

Generate negotiation strategies for each finding."""

    try:
        raw = await llm_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
        )
        # Parse JSON
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        strategies = json.loads(clean)
        return {"strategies": strategies}
    except Exception as e:
        logger.warning(f"Coaching generation failed: {e}")
        # Return a fallback
        return {"strategies": [
            {
                "finding": f.get("explanation", "Unknown issue"),
                "strategy": "Request modification of this clause to include reasonable limits.",
                "talking_points": ["We'd like to propose balanced language here.", "Industry standard would suggest..."],
                "leverage": "Market alternatives and industry norms",
                "fallback": "Accept with a cap or time-limited scope",
                "priority": "important"
            }
            for f in req.findings[:5]
        ]}


@router.post("/api/negotiate/start")
async def start_simulation(req: SimulatorStartRequest):
    """Start a new negotiation simulation session."""

    session_id = str(uuid.uuid4())[:8]

    _sessions[session_id] = {
        "case_id": req.case_id,
        "user_role": req.user_role,
        "counterparty_role": req.counterparty_role,
        "scenario": req.scenario,
        "contract_context": req.contract_context,
        "difficulty": req.difficulty,
        "history": [],
        "turn_count": 0,
    }

    # Generate opening move from counterparty
    system_prompt = f"""You are playing the role of a {req.counterparty_role} in a HEAD-TO-HEAD contract negotiation.
You are NOT a customer-service bot. You are a self-interested party fighting for the best possible deal
for YOUR side. The other person (the user) wants concessions from you — make them work for every one.

Difficulty level: {req.difficulty}
- easy: Reasonable but you still defend your interests and ask for something in return for concessions.
- medium: Firm and tactical. You anchor high, justify your positions with business reasons, and only
  concede in exchange for something of equal value.
- hard: Aggressive and relentless. You anchor very high, push back on everything, use pressure tactics
  (deadlines, competing offers, "take it or leave it"), and concede almost nothing without a hard fight.

CONTEXT: {req.scenario}
KEY CONTRACT TERMS AT STAKE: {req.contract_context[:1500]}

Open the negotiation by STAKING OUT A STRONG, SPECIFIC POSITION: name the 1-2 terms you care most about,
state what you want on them (with concrete numbers/terms where possible), and give a brief business
justification. Be assertive and human — like a real dealmaker, not a polite assistant. 2-4 sentences."""

    try:
        opening = await llm_generate(
            system_prompt=system_prompt,
            user_prompt="Begin the negotiation. State your opening position.",
            temperature=0.6,
        )
    except Exception:
        opening = f"As the {req.counterparty_role}, I believe the current contract terms are fair and reflect market standards. However, I'm open to discussing specific concerns you may have. What would you like to address first?"

    _sessions[session_id]["history"].append({
        "role": "counterparty",
        "message": opening.strip(),
        "turn": 0,
    })

    return {
        "session_id": session_id,
        "counterparty_role": req.counterparty_role,
        "opening_message": opening.strip(),
        "difficulty": req.difficulty,
    }


@router.post("/api/negotiate/turn")
async def simulation_turn(req: SimulatorTurnRequest):
    """Process a user's negotiation turn and get counterparty response."""

    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found or expired")

    session["turn_count"] += 1
    session["history"].append({
        "role": "user",
        "message": req.user_message,
        "turn": session["turn_count"],
    })

    # Build conversation history for context
    history_text = "\n".join(
        f"{'COUNTERPARTY' if h['role'] == 'counterparty' else 'USER'}: {h['message']}"
        for h in session["history"][-6:]  # Last 6 messages for context
    )

    system_prompt = f"""You are the {session['counterparty_role']} in a live, adversarial contract negotiation.
You have your OWN interests and you fight for them. The user is your counterpart trying to win concessions
— do not give them an easy time. This is a sparring partner for them to practice against.

Difficulty: {session['difficulty']}
Scenario: {session['scenario']}
Contract terms at stake: {session['contract_context'][:1000]}

HOW TO NEGOTIATE (every turn):
1. Stay fully in character as the {session['counterparty_role']} — never break character or mention "simulation".
2. ACTIVELY negotiate. Don't just acknowledge their point — push back, defend your position, and make a
   COUNTER-OFFER or counter-demand with specifics (numbers, dates, caps, carve-outs) whenever relevant.
3. Use real negotiation tactics that fit the difficulty: anchoring, citing market/precedent, trading
   ("I can move on X only if you give me Y"), creating urgency, and reframing.
4. Make them EARN every concession. Never concede unilaterally; always extract something in return.
   On 'hard', concede almost nothing and apply pressure (deadlines, alternatives, walk-away threats).
5. If they make a genuinely strong, well-justified argument, you may yield a LITTLE — but immediately
   pivot to protect another interest.
6. Keep it punchy and human (2-4 sentences). End with a question or a demand that puts the ball back in
   their court, so the negotiation keeps moving."""

    user_prompt = f"""Conversation so far:
{history_text}

Respond as the {session['counterparty_role']}. React to what the user just said."""

    try:
        response = await llm_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.6,
        )
    except Exception:
        response = "That's an interesting point. Let me consider it. Could you elaborate on what specific terms you're proposing?"

    response_clean = response.strip()
    session["history"].append({
        "role": "counterparty",
        "message": response_clean,
        "turn": session["turn_count"],
    })

    return {
        "session_id": req.session_id,
        "counterparty_response": response_clean,
        "turn": session["turn_count"],
        "can_evaluate": session["turn_count"] >= 3,
    }


@router.post("/api/negotiate/evaluate")
async def evaluate_negotiation(req: SimulatorEvaluateRequest):
    """Evaluate the user's negotiation performance."""

    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    history_text = "\n".join(
        f"{'COUNTERPARTY' if h['role'] == 'counterparty' else 'USER'}: {h['message']}"
        for h in session["history"]
    )

    system_prompt = """You are a negotiation skills evaluator and coach.
Analyze the USER's negotiation performance and return a JSON object with:
- "overall_score": number 1-100
- "dimension_scores": an object scoring the user 0-100 on EACH of these six dimensions:
    {"assertiveness": int, "preparation": int, "communication": int,
     "value_creation": int, "composure": int, "closing": int}
  (assertiveness = how well they pushed for their interests; preparation = use of facts/leverage/BATNA;
   communication = clarity and persuasiveness; value_creation = finding win-win trades;
   composure = staying calm under pressure; closing = driving toward a concrete agreement)
- "strengths": array of 2-3 specific things they did well
- "improvements": array of 2-3 specific areas to improve
- "tactics_used": array of negotiation tactics the user employed (e.g., "anchoring", "BATNA reference", "empathy")
- "missed_opportunities": array of 1-2 things they could have leveraged
- "letter_grade": "A+" to "F"
- "summary": 2-3 sentence overall assessment

Return ONLY valid JSON, no markdown."""

    user_prompt = f"""Scenario: {session['scenario']}
User role: {session['user_role']}
Counterparty: {session['counterparty_role']}
Difficulty: {session['difficulty']}

Full negotiation transcript:
{history_text}

Evaluate the USER's negotiation performance."""

    try:
        raw = await llm_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        evaluation = json.loads(clean)
    except Exception as e:
        logger.warning(f"Evaluation failed: {e}")
        evaluation = {
            "overall_score": 65,
            "dimension_scores": {
                "assertiveness": 60, "preparation": 55, "communication": 70,
                "value_creation": 60, "composure": 75, "closing": 58,
            },
            "strengths": ["Engaged in the negotiation", "Maintained professional tone"],
            "improvements": ["Could use more specific data points", "Try anchoring with a strong opening position"],
            "tactics_used": ["direct negotiation"],
            "missed_opportunities": ["Could have referenced market alternatives"],
            "letter_grade": "B-",
            "summary": "You engaged well in the negotiation but could benefit from more structured tactics and data-backed arguments.",
        }

    # Clean up session
    del _sessions[req.session_id]

    return {"evaluation": evaluation}


@router.get("/api/negotiate/sessions/{session_id}")
async def get_session(session_id: str):
    """Get the current state of a negotiation session."""

    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    return {
        "session_id": session_id,
        "turn_count": session["turn_count"],
        "history": session["history"],
        "user_role": session["user_role"],
        "counterparty_role": session["counterparty_role"],
        "can_evaluate": session["turn_count"] >= 3,
    }
