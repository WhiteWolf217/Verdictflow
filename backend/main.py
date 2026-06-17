"""
VerdictFlow Backend — Multi-Agent Contract Intelligence System

FastAPI application entry point with CORS, lifespan management,
and router includes.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from api.routes import router as api_router  # noqa: E402
from core.vectorstore import VectorStoreManager  # noqa: E402

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s │ %(name)-20s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("verdictflow")


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 VerdictFlow starting up...")

    # Initialize Qdrant vector store
    vs = VectorStoreManager()
    vs.ensure_collection()
    # Seed the market-standard precedent library (idempotent). Non-fatal on failure.
    try:
        vs.seed_precedents()
    except Exception as e:
        logger.warning(f"⚠️  Precedent library seeding failed: {e}")
    app.state.vectorstore = vs
    logger.info("✅ Qdrant vector store initialized")

    # Initialize AgentOps (optional)
    agentops_key = os.getenv("AGENTOPS_API_KEY")
    if agentops_key:
        try:
            import agentops
            agentops.init(api_key=agentops_key)
            logger.info("✅ AgentOps observability initialized")
        except ImportError:
            logger.warning("⚠️  AgentOps package not installed, skipping")
    else:
        logger.info("⏭️  AgentOps API key not set, skipping")

    # Band case-room coordination. Always available: uses the Band SDK when
    # installed/configured, otherwise built-in in-memory case rooms.
    try:
        from band.client import BandClientWrapper
        band_client = BandClientWrapper()
        app.state.band_client = band_client
        logger.info(f"✅ Band case-room coordination ready (mode={band_client.mode})")
    except Exception as e:
        logger.warning(f"⚠️  Band client init failed: {e}")
        app.state.band_client = None

    logger.info("🟢 VerdictFlow ready — all systems nominal")
    yield

    # Shutdown
    logger.info("🔴 VerdictFlow shutting down...")


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="VerdictFlow",
    description="Multi-Agent Contract Intelligence System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend origin
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "verdictflow"}
