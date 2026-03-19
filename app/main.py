"""
JODOHKU.MY — Main Application Entry Point
FastAPI backend with all routes mounted

Run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db

# Import all route modules
from app.routes import auth, profile, quiz, gallery, chat, payment, notifications, wali, settings as settings_routes, admin

config = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Jodohku.my API",
    description="Premium Islamic Matchmaking Platform — Backend API v2.0",
    version=config.app_version,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
    lifespan=lifespan,
)


# ─── CORS ───
# Allow all jodohku.my origins + Render URL

ALLOWED_ORIGINS = [
    "https://jodohku.my",
    "https://www.jodohku.my",
    "https://jodohku-frontend.vercel.app",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5500",
]

# Also allow any extra origins from .env
if config.cors_origins:
    for origin in config.cors_origins:
        if origin not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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


from app.utils.seed import run_seed

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await run_seed()  # ← add this
    yield
    await close_db()
