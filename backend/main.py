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

    # Band case-room coordination via REST API.
    try:
        from band.client import BandClientWrapper
        band_client = BandClientWrapper()
        app.state.band_client = band_client
        logger.info(f"✅ Band case-room coordination ready (mode={band_client.mode})")

        # Verify every agent identity with the Band platform.
        if band_client.is_available:
            logger.info("🔎 Verifying all Band agent identities...")
            results = await band_client.verify_all_agents()
            ok_count = sum(1 for v in results.values() if v)
            if ok_count == len(results):
                logger.info(f"✅ All {ok_count} Band agents verified and ready")
            else:
                logger.warning(
                    f"⚠️  Only {ok_count}/{len(results)} Band agents verified — "
                    "check the rejected keys above"
                )
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
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Include Negotiation routes
from api.negotiate import router as negotiate_router  # noqa: E402
app.include_router(negotiate_router)

# Include standout feature routes (chat, debate, counter-draft, negotiation email)
from api.features import router as features_router  # noqa: E402
app.include_router(features_router)

# Include contract version comparison
from api.compare import router as compare_router  # noqa: E402
app.include_router(compare_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "verdictflow"}
