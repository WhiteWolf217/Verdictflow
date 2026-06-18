# VerdictFlow 🔍⚖️

**Multi-Agent Contract Intelligence System** — Built for the Band of Agents Hackathon

VerdictFlow uses 6 specialized AI agents coordinated through a Band shared case room to review, red-team, and redline enterprise contracts. The output is a human-gated, tamper-evident audit packet.

## Architecture

```
Contract Upload → Intake Agent → [Clause Analyst | Red Team | Financial Risk] → Compliance → Redline → Human Gate → Audit Packet
```

### The 6 Agents

| Agent | Framework | Model | Role |
|-------|-----------|-------|------|
| **Intake** | Pydantic AI | Claude Sonnet 4.6 | Parse, chunk, classify, index |
| **Clause Analyst** | LangChain + RAG | Claude Sonnet 4.6 | Clause-by-clause risk analysis |
| **Red Team** | CrewAI | Featherless AI | Adversarial attack/defend review |
| **Financial Risk** | LangChain | GPT-4o / Claude | Quantify financial exposure |
| **Compliance** | Pydantic AI | Claude Sonnet 4.6 | Regulatory compliance checks |
| **Redline** | Anthropic API | Claude Sonnet 4.6 | Generate redline edits |

### Tech Stack

- **Backend**: Python 3.11, FastAPI, SSE, LangGraph orchestrator
- **Frontend**: Next.js 14 (App Router), TypeScript, TailwindCSS
- **Coordination**: Band SDK shared case rooms
- **Vector Store**: Qdrant (local Docker)
- **Observability**: AgentOps

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for Qdrant)

### 1. Start Qdrant
```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 2. Backend Setup
```bash
cd verdictflow/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your API keys
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd verdictflow/frontend
npm install
cp .env.example .env.local
npm run dev
```

### 4. Open Dashboard
Navigate to `http://localhost:3000`

## Environment Variables

See `backend/.env.example` for the full list. Required:
- `ANTHROPIC_API_KEY` — Claude Sonnet 4.6
- `BAND_API_KEY` + `BAND_WORKSPACE_ID` — Band SDK
- `FEATHERLESS_API_KEY` — Open-source models
- `QDRANT_URL` — Vector store (default: `http://localhost:6333`)

## License

MIT
