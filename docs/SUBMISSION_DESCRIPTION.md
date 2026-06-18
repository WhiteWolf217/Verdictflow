# VerdictFlow — Hackathon Submission Description

## Title

**VerdictFlow — Multi-Agent Contract Intelligence**

## Tagline

A band of 6 adversarial AI agents reviews, red-teams, and redlines enterprise contracts in under 3 minutes — with a human-gated, tamper-evident audit trail.

## Problem

B2B contract review takes **4+ hours per contract** and costs **$200–$800** in attorney time. Mid-market companies have no access to AI-powered contract review tools at reasonable cost. Single-agent systems lack adversarial validation — they either flag everything (alert fatigue) or miss critical risks (dangerous).

Key pain points:
- Legal teams are bottlenecked by volume — every NDA, SaaS agreement, and vendor contract needs manual review
- Non-standard clauses (overbroad IP assignments, missing liability caps, GDPR gaps) slip through when reviewers are fatigued
- No audit trail proves *how* a decision was reached, creating liability gaps

## Solution

VerdictFlow deploys **6 specialized AI agents** coordinated through a Band shared case room to review, challenge, and redline any enterprise contract:

| Agent | Role | Model |
|-------|------|-------|
| **Intake Agent** | Parse document, extract metadata, index into Qdrant | Claude Sonnet 4.6 |
| **Clause Analyst** | RAG-grounded clause-by-clause analysis against 15 market-standard precedents | Claude Sonnet 4.6 + Qdrant |
| **Red Team (Attacker/Defender)** | Adversarial stress-testing — find vulnerabilities, then validate them | Featherless AI (Qwen2.5-72B) |
| **Financial Risk Agent** | Quantify monetary exposure, identify penalty clauses and liability gaps | GPT-4o / Claude Sonnet 4.6 |
| **Compliance Agent** | Cross-check GDPR, CCPA, HIPAA, SOX regulations | Claude Sonnet 4.6 |
| **Redline Agent** | Draft specific edits (original → proposed) with rationale | Claude Sonnet 4.6 |

After all agents run, the **Adjudicator** synthesizes findings into a final verdict: **APPROVE**, **APPROVE WITH CHANGES**, or **DO NOT SIGN** — with a deterministic confidence score.

Every finding is posted to the Band case room. Every step is SHA-256 hash-chained into a **tamper-evident audit trail**. The human reviewer always has the final say through a **human gate** before the audit packet is sealed.

## Technical Innovation

### Multi-Agent Adversarial Dynamics
The Red Team uses an **Attacker/Defender pattern**: the Attacker finds every possible vulnerability, and the Defender filters out false positives. Only validated findings survive. This eliminates alert fatigue and builds trust in the results.

### RAG-Grounded Analysis
The Clause Analyst compares contract clauses against a **15-clause market-standard precedent library** indexed in Qdrant with local CPU embeddings (sentence-transformers/all-MiniLM-L6-v2). Findings are grounded in real-world standards, not hallucinated.

### Tamper-Evident Audit Trail
Every agent action is recorded as a SHA-256 hash-chained entry. The chain can be independently verified at any time. The DOCX audit report includes the chain fingerprint in its footer.

### Band Coordination
All agents communicate through a shared Band case room, creating a full conversation transcript of the review process. This transparency is critical for regulated industries.

### Deterministic + Narrative Verdicts
The Adjudicator computes the recommendation and confidence score **deterministically** from findings metrics (so they're always available), then uses Claude to write a professional 3-paragraph narrative verdict on top. If the LLM fails, the deterministic fallback ensures the system never returns empty results.

### Tolerant Enum Coercion
LLMs often return slightly-off enum values ("moderate", "SEVERE ", "Non-Compliant"). VerdictFlow's coercion layer maps these to valid values instead of dropping findings — making the system robust in production.

## Tech Stack

- **Backend**: Python 3.11, FastAPI, uvicorn, SSE (Server-Sent Events)
- **Frontend**: Next.js 14 (App Router), TypeScript, TailwindCSS
- **LLMs**: Claude Sonnet 4.6 (Anthropic), Featherless AI (Qwen2.5-72B), GPT-4o (optional)
- **Vector Store**: Qdrant with FastEmbed (local CPU embeddings)
- **Coordination**: Band SDK (with fully-functional in-memory fallback)
- **Observability**: AgentOps (optional)
- **Document Processing**: PyMuPDF, python-docx

## Key Features

- 📄 **Upload any contract** — PDF, DOCX, or TXT
- 🔍 **6-agent pipeline** — clause analysis, red teaming, financial risk, compliance, redlining
- 🔴 **Adversarial validation** — Attacker/Defender pattern eliminates false positives
- 📊 **Real-time streaming** — SSE live feed shows agent activity as it happens
- 🔒 **Human gate** — approve or reject with feedback before sealing
- 🔗 **Tamper-evident audit** — SHA-256 hash chain with independent verification
- 📥 **DOCX export** — professional audit report with tracked-changes redlines
- 🏠 **Band case room** — full agent conversation transcript, inspectable via API

## Tracks

- **Track 3: Regulated Workflows** — tamper-evident audit trail, compliance checking, human-gated output
- **AI/ML API Prize** — Claude Sonnet 4.6 powers 5 of 6 agents
- **Featherless AI Prize** — Red Team Attacker uses Featherless AI (Qwen2.5-72B-Instruct)
