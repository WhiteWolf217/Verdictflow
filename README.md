# VerdictFlow ⚖️🤖

**Multi-Agent Contract Intelligence System** — Built for the AMD Hackathon

VerdictFlow uses specialized AI agents to review, red-team, compare, and negotiate enterprise contracts. Instead of a single LLM trying to do everything, VerdictFlow utilizes an architecture where distinct agents (Clause Analyst, Red Team, Compliance, Adjudicator) perform deep analysis and actively debate each other in real-time to reach a consensus.

## ✨ Key Features

### 1. 🎙️ Live Agent Boardroom (Cross-Examination)
The standout feature. Agents don't just run in parallel—they **argue**. Watch in real-time as the **Red Team Agent** challenges the findings of the **Clause Analyst**, while the **Adjudicator** steps in to resolve disputes and forge a final consensus. The live debate streams directly into a sidebar pinned to the right of the screen.

### 2. 🆚 Contract Version Compare & Risk Delta
Upload V1 and V2 of a contract simultaneously. The multi-agent pipeline analyzes the exact diffs and calculates the **Risk Delta**, telling you instantly whether the new version increased or decreased your legal exposure.

### 3. 🎤 Real-Time Voice Negotiation Simulator
Practice negotiating the contract against an AI counterpart using the **Web Speech API**. Click the mic, speak your arguments, and get immediate counter-arguments and scoring based on Assertiveness, Preparation, and Communication.

### 4. 🛡️ Tamper-Evident Audit Packets
Every finding, debate, and redline edit is compiled into a cryptographically hashed, immutable Audit Packet, ensuring complete transparency and accountability for enterprise compliance teams.

## 🧠 The Agent Architecture

| Agent | Role |
|-------|------|
| **Intake Agent** | Parses, chunks, classifies, and indexes the document. |
| **Clause Analyst** | Performs initial clause-by-clause risk and liability analysis. |
| **Red Team** | Adversarially attacks the Analyst's findings looking for missed loopholes. |
| **Financial Risk** | Quantifies financial exposure and flags uncapped liabilities. |
| **Compliance** | Checks against regulatory frameworks (GDPR, CCPA, etc.). |
| **Adjudicator** | The final judge. Resolves disputes between the Red Team and Analyst. |
| **Redline** | Generates inline tracked changes based on the Adjudicator's final rulings. |

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, Server-Sent Events (SSE) for live streaming.
- **Frontend**: Next.js 14, React, TailwindCSS, Web Speech API.
- **LLM Engine**: Powered by Groq (Llama 3.3 70B) for ultra-low latency inference, enabling real-time multi-agent debates, and Google Gemini 1.5 Pro.
- **Vector Store**: Qdrant (local/Docker).

## 🚀 Deployment Instructions

Due to the long-running nature of the Multi-Agent debates (which use Server-Sent Events), the frontend and backend must be deployed separately.

### 1. Deploy the Backend (Railway / Render)
Vercel's strict serverless timeouts will kill the agent pipeline. Deploy the backend to a dedicated host like Railway.
1. Push this repo to GitHub.
2. Go to [Railway.app](https://railway.app), create a new project from your repo.
3. Set the Root Directory to `/verdictflow/backend`.
4. Add your API Keys (`GROQ_API_KEY`, `GEMINI_API_KEY`) to the Railway environment variables.
5. Deploy. Copy the generated Railway URL.

### 2. Deploy the Frontend (Vercel)
1. Go to [Vercel](https://vercel.com), add a new project from your repo.
2. Set the Root Directory to `/verdictflow/frontend`.
3. Add the Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `[YOUR_RAILWAY_URL]`
4. Deploy.

## 💻 Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for Qdrant Vector DB)

### 1. Start Vector Database
```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 2. Backend
```bash
cd verdictflow/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
# Add Groq/Gemini API keys to .env
uvicorn main:app --reload --port 8000
```

### 3. Frontend
```bash
cd verdictflow/frontend
npm install
npm run dev
```
Navigate to `http://localhost:3000` to see the dashboard.

## 📄 License
MIT License
