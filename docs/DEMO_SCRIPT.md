# VerdictFlow — Demo Script (6 Minutes)

> Use this script for the hackathon demo video submission. Estimated runtime: 5–6 minutes.

---

## Minute 0:00–0:30 — Problem Statement

> **Talking point:**
>
> "B2B companies waste 4+ hours manually reviewing every contract — NDAs, SaaS agreements, MSAs. Small legal teams miss critical risks: overbroad IP assignments, missing liability caps, GDPR gaps. And single-agent AI tools lack adversarial validation — they flag everything or nothing.
>
> VerdictFlow deploys a **band of 6 specialized AI agents** to review, red-team, and redline any contract in under 3 minutes — with a human-gated, tamper-evident audit trail."

---

## Minute 0:30–1:00 — Architecture Overview

> **Show:** The architecture diagram from `docs/architecture.md` or a slide.

> **Talking point:**
>
> "Here's how VerdictFlow works. When you upload a contract, it flows through 6 agents coordinated via a Band shared case room:
>
> 1. **Intake Agent** — parses the document and indexes it into Qdrant for RAG
> 2. **Clause Analyst** — compares every clause against a market-standard precedent library
> 3. **Red Team** — an Attacker/Defender pair that stress-tests the contract for exploitable loopholes
> 4. **Financial Risk Agent** — quantifies monetary exposure
> 5. **Compliance Agent** — checks against GDPR, CCPA, HIPAA, SOX
> 6. **Redline Agent** — drafts specific edits for risky clauses
>
> Then the **Adjudicator** synthesizes everything into a final verdict — APPROVE, APPROVE WITH CHANGES, or DO NOT SIGN.
>
> Every finding posts to the Band case room. Every step is cryptographically hashed into a tamper-evident audit chain."

---

## Minute 1:00–2:30 — Live Demo: Upload & Agent Activity

> **Action:** Open the VerdictFlow UI. Upload `contracts/sample_nda.txt`.

> **Talking point (narrate as agents run):**
>
> "Let's upload a real NDA. Watch the agent activity feed on the left — each agent runs in sequence, posting findings as it goes.
>
> See the **Clause Analyst** flagging this perpetual confidentiality clause — it has no sunset and no carve-out for public information. That's a HIGH risk.
>
> Now the **Red Team** is attacking — it found a loophole in the non-compete clause. The Attacker flagged it, and the Defender validated it's a real vulnerability.
>
> The **Financial Risk Agent** just scored the exposure. And the **Compliance Agent** caught a GDPR gap — there's personal data language but no Data Processing Agreement reference.
>
> Finally, the **Redline Agent** is drafting specific rewrites for the risky clauses — original in red, proposed in green."

---

## Minute 2:30–3:30 — Human Gate: Review Findings

> **Action:** Show the case detail page. Walk through the tabs.

> **Talking point:**
>
> "Now let's review what the agents found. The Overview tab shows the risk summary at a glance — total findings, critical issues, financial exposure.
>
> Switch to Findings — we can see each clause flag with risk level, explanation, and specific recommendations.
>
> The Red Team tab shows validated adversarial attacks — the Defender confirmed these are real vulnerabilities.
>
> And here are the Redlines — side-by-side original versus proposed text. Each edit has a priority: required, recommended, or optional.
>
> The Audit Trail tab shows every step in a cryptographic hash chain. Click 'Verify Chain' — the integrity check passes. No data was tampered with."

---

## Minute 3:30–4:30 — Approve & Download

> **Action:** Click Approve. Download the DOCX report.

> **Talking point:**
>
> "I'm satisfied with the review. I'll add a note and click Approve.
>
> The audit packet is now sealed. Notice the SHA-256 hash — this is the tamper-evident fingerprint of the entire review.
>
> Let me download the DOCX audit report. Open it — you can see the executive verdict, financial risk summary, clause flags as a table, compliance issues, and the proposed redlines with red strikethrough for the original and green for the proposed text. This is a professional document you can send to your legal team or attach to the contract file."

---

## Minute 4:30–5:30 — Technical Differentiation

> **Talking point:**
>
> "What makes VerdictFlow unique:
>
> 1. **Multi-agent adversarial dynamics** — the Red Team challenges every finding before it reaches the human. This eliminates false positives.
>
> 2. **RAG-grounded analysis** — the Clause Analyst compares against a 15-clause market-standard precedent library stored in Qdrant. Findings are grounded, not hallucinated.
>
> 3. **Tamper-evident audit trail** — every agent action is SHA-256 hash-chained. You can verify integrity at any time.
>
> 4. **Human-gated output** — no contract decision is fully automated. The human always has the final say.
>
> 5. **Band coordination** — all agents communicate through a shared case room. You can inspect the full agent conversation thread."

---

## Minute 5:30–6:00 — Business Case & Closing

> **Talking point:**
>
> "This workflow takes 4+ hours manually. VerdictFlow does it in under 3 minutes, with an evidence trail no single-agent system can match.
>
> Mid-market companies spend $200–$800 in attorney time per contract. VerdictFlow brings enterprise-grade contract intelligence to teams of any size.
>
> Thank you."

---

## Pre-Demo Checklist

- [ ] Backend running (`uvicorn main:app --reload --port 8000`)
- [ ] Qdrant running (`docker-compose up -d`)
- [ ] Frontend running (`cd frontend && npm run dev`)
- [ ] API keys set in `.env` (at minimum: `ANTHROPIC_API_KEY`)
- [ ] Sample contracts ready in `contracts/` directory
- [ ] Browser open to `http://localhost:3000`
