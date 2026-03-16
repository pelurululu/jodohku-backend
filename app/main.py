"""
JODOHKU.MY — Main Application Entry Point
FastAPI backend with all routes mounted

Run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.database import init_db, close_db

# Import all route modules
from app.routes import auth, profile, quiz, gallery, chat, payment, notifications, wali, settings as settings_routes, admin

config = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Jodohku.my API",
    description="Premium Islamic Matchmaking Platform — Backend API v2.0",
    version=config.app_version,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
    lifespan=lifespan,
)


# ─── Middleware ───

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jodohku.my",
        "https://www.jodohku.my",
        "https://jodohku-api.onrender.com",
        "*",  # sementara untuk debug
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if config.app_env == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "api.jodohku.my",
            "*.jodohku.my",
            "jodohku-api.onrender.com",  # ← tambah ini
            "*.onrender.com",             # ← dan ini
        ],
    )


# ─── Mount API Routes ───

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(profile.router, prefix=API_PREFIX)
app.include_router(quiz.router, prefix=API_PREFIX)
app.include_router(gallery.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(payment.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(wali.router, prefix=API_PREFIX)
app.include_router(settings_routes.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


# ─── Health Check ───

@app.get("/health")
async def health_check():
    return {
        "status": "operational",
        "version": config.app_version,
        "service": "Jodohku.my API",
    }


@app.get("/")
async def root():
    return {
        "message": "Pencarian Sekufu Bermula Di Sini",
        "api_docs": "/docs" if config.debug else "Disabled in production",
    }
