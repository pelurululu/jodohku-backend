"""
JODOHKU.MY — Main Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import init_db, close_db, get_db
from app.routes import auth, profile, quiz, gallery, chat, payment, notifications, wali, settings as settings_routes, admin

config = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Auto-seed on startup
    try:
        from app.utils.seed import run_seed
        await run_seed()
    except Exception as e:
        print(f"[Seed] Skipped or failed: {e}")
    yield
    await close_db()


app = FastAPI(
    title="Jodohku.my API",
    description="Premium Islamic Matchmaking Platform",
    version=config.app_version,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jodohku.my",
        "https://www.jodohku.my",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Routes ──
API_PREFIX = "/api/v1"
app.include_router(auth.router,               prefix=API_PREFIX)
app.include_router(profile.router,            prefix=API_PREFIX)
app.include_router(quiz.router,               prefix=API_PREFIX)
app.include_router(gallery.router,            prefix=API_PREFIX)
app.include_router(chat.router,               prefix=API_PREFIX)
app.include_router(payment.router,            prefix=API_PREFIX)
app.include_router(notifications.router,      prefix=API_PREFIX)
app.include_router(wali.router,               prefix=API_PREFIX)
app.include_router(settings_routes.router,    prefix=API_PREFIX)
app.include_router(admin.router,              prefix=API_PREFIX)


@app.get("/health")
async def health_check():
    return {"status": "operational", "version": config.app_version, "service": "Jodohku.my API"}


@app.post("/api/v1/admin/compute-matches")
async def compute_all_matches(db: AsyncSession = Depends(get_db)):
    from app.services.matching_service import MatchingService
    from app.models.user import User
    from sqlalchemy import select
    result = await db.execute(select(User))
    users = result.scalars().all()
    total = 0
    for user in users:
        svc = MatchingService(db)
        n = await svc.compute_matches_for_user(user.id)
        total += n
    return {"users": len(users), "matches": total}


@app.get("/")
async def root():
    return {"message": "Pencarian Sekufu Bermula Di Sini"}
