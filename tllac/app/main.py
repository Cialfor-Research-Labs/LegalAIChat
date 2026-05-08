"""
TLLAC (Trained Legal AI Chat) — FastAPI Backend
=================================================
Fully isolated backend for the Experimental Chat UI.
Runs on port 9001. Must NOT import or depend on any existing LAW LLM module.

Start with:
    uvicorn app.main:app --reload --port 9001
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.chat import router as chat_router
from .routes.legal_notice import router as legal_notice_router

# ──────────────────────────────────────────────
# Application Instance
# ──────────────────────────────────────────────
app = FastAPI(
    title="Trained Legal AI Chat Backend (TLLAC)",
    description="Isolated backend serving the experimental chat UI. "
                "Provides Indian legal and legal-adjacent responses.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ──────────────────────────────────────────────
# CORS — Allow development access
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────
app.include_router(chat_router)
app.include_router(legal_notice_router)


# ──────────────────────────────────────────────
# Health / Root
# ──────────────────────────────────────────────
@app.get("/")
async def root():
    """Health-check endpoint."""
    return {
        "status": "online",
        "service": "TLLAC — Trained Legal AI Chat",
        "version": "1.0.0",
        "port": 9001,
        "isolation": "indian-legal",
    }
