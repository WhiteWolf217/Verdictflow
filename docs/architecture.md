# VerdictFlow — Architecture Documentation

## System Overview

VerdictFlow is a multi-agent contract intelligence system that uses 6 specialized AI agents,
coordinated through Band SDK shared case rooms, to review, red-team, and redline enterprise
contracts. The output is a human-gated, tamper-evident audit packet.

## Agent Pipeline

```
┌───────────────────────────────────────────────────────────────────┐
│                        VERDICTFLOW PIPELINE                       │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌──────────┐                                                   │
│   │  INTAKE   │  Parse → Chunk → Index → Classify                │
│   └────┬─────┘                                                   │
│        │                                                         │
│   ┌────┴──────────────────────────────────┐                      │
│   │         PARALLEL ANALYSIS             │                      │
│   │  ┌────────────┐ ┌─────────┐ ┌───────┐│                      │
│   │  │   CLAUSE   │ │RED TEAM │ │FINANCE││                      │
│   │  │  ANALYST   │ │ATTACKER │ │ RISK  ││                      │
│   │  │  (RAG)     │ │DEFENDER │ │       ││                      │
│   │  └────┬───────┘ └────┬────┘ └───┬───┘│                      │
│   └────────┼─────────────┼──────────┼────┘                      │
│            └─────────────┼──────────┘                            │
│                          ▼                                       │
│                    ┌──────────┐                                   │
│                    │COMPLIANCE│  GDPR / SOX / HIPAA / CCPA       │
│                    └────┬─────┘                                   │
│                         ▼                                        │
│                    ┌──────────┐                                   │
│                    │ REDLINE  │  Synthesize → Edit Suggestions    │
│                    └────┬─────┘                                   │
│                         ▼                                        │
│                    ┌──────────┐                                   │
│                    │  HUMAN   │  Approve / Reject                 │
│                    │   GATE   │                                   │
│                    └────┬─────┘                                   │
│                         ▼                                        │
│                    ┌──────────┐                                   │
│                    │  AUDIT   │  Sealed, Tamper-Evident Packet    │
│                    │  PACKET  │                                   │
│                    └──────────┘                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Agent Details

### 1. Intake Agent
- **Framework**: Pydantic AI
- **Model**: Claude Sonnet 4.6
- **Input**: Uploaded PDF or DOCX file
- **Process**: Parse → Chunk (512 tokens, 10% overlap) → Index to Qdrant → Classify via LLM
- **Output**: ContractMetadata + indexed vector chunks

### 2. Clause Analyst
- **Framework**: LangChain + RAG
- **Model**: Claude Sonnet 4.6
- **Input**: Contract text + Qdrant vector store
- **Process**: For each of 12 clause categories, perform semantic search → analyze with LLM
- **Output**: list[ClauseFinding] with risk levels

### 3. Red Team Agent
- **Framework**: CrewAI-style (Attacker/Defender)
- **Model**: Featherless AI (Qwen2.5-72B-Instruct)
- **Input**: Contract text
- **Process**: Attacker finds vulnerabilities → Defender validates/filters
- **Output**: list[RedTeamAttack] with validated severities

### 4. Financial Risk Agent
- **Framework**: LangChain
- **Model**: GPT-4o (fallback: Claude Sonnet 4.6)
- **Input**: Contract text
- **Process**: Identify financial terms → Quantify exposure
- **Output**: list[FinancialRisk] with exposure amounts

### 5. Compliance Agent
- **Framework**: Pydantic AI
- **Model**: Claude Sonnet 4.6
- **Input**: Contract text + doc_type + governing_law
- **Process**: Check against applicable regulations
- **Output**: list[ComplianceCheck] with remediation steps

### 6. Redline Agent
- **Framework**: Direct Anthropic API
- **Model**: Claude Sonnet 4.6
- **Input**: All prior findings + contract text
- **Process**: Synthesize findings → Generate specific edit suggestions
- **Output**: list[RedlineEdit] with priorities

## Tamper-Evident Audit Trail

The audit trail uses SHA-256 hash chaining:

```
Entry 0          Entry 1          Entry 2
┌──────────┐    ┌──────────┐    ┌──────────┐
│ data_hash│    │ data_hash│    │ data_hash│
│ prev: 000│───→│ prev: h0 │───→│ prev: h1 │
│ hash: h0 │    │ hash: h1 │    │ hash: h2 │
└──────────┘    └──────────┘    └──────────┘
```

Each entry contains:
- `step_index`: Sequential position
- `agent_name`: Which agent produced this entry
- `action`: What happened
- `data_hash`: SHA-256 of the agent's output data
- `previous_hash`: Hash of the previous entry (chain link)
- `current_hash`: SHA-256 of (step_index + agent_name + action + data_hash + previous_hash + timestamp)

Verification: Iterate through all entries, recompute each hash, and verify linkage.

## Band SDK Coordination

Each case gets a shared Band chatroom where agents:
1. Post findings as messages
2. Broadcast stage events (INTAKE_COMPLETE, etc.)
3. Share context across framework boundaries

The Band SDK enables cross-framework interoperability — agents built with
Pydantic AI, LangChain, and CrewAI all communicate through the same room.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Frontend | Next.js 14, TypeScript, TailwindCSS |
| Streaming | Server-Sent Events (SSE) |
| Orchestration | LangGraph state graph |
| Agent Coordination | Band SDK |
| Vector Store | Qdrant + FastEmbed |
| Document Processing | PyMuPDF, python-docx |
| Observability | AgentOps |
| Models | Claude Sonnet 4.6, GPT-4o, Featherless AI |
