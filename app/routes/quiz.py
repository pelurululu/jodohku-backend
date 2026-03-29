"""
JODOHKU.MY — Quiz Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import QuizAnswerRequest, QuizBatchAnswerRequest, PsychometricScoreResponse
from app.services.quiz_service import QuizService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/quiz", tags=["Psychometric Quiz"])


@router.get("/questions")
async def get_quiz_questions(
    batch: str = "core",
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = QuizService(db)
    # FIX: convert string batch to int the service expects
    batch_int = 1 if batch == "core" else 2
    result = await service.get_questions(current_user.id, batch_int)
    # service already returns {"questions": [...], "total": n, "answered": n}
    # spread it so the frontend gets d.questions as a plain array, not nested
    return {**result, "batch": batch}


@router.post("/answer")
async def submit_answer(
    request: QuizAnswerRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = QuizService(db)
    # FIX: submit_answer only returns success/question_id/score
    # so we fetch progress separately
    await service.submit_answer(
        current_user.id,
        request.question_id,
        request.score,
        request.time_taken_seconds,
    )
    progress = await service.get_progress(current_user.id)
    return {
        "saved": True,
        "progress": progress,
        "gallery_unlocked": progress.get("gallery_unlocked", False),
    }


@router.post("/answers/batch")
async def submit_batch_answers(
    request: QuizBatchAnswerRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = QuizService(db)
    result = await service.submit_batch(current_user.id, request.answers)
    return result


@router.get("/score")
async def get_my_score(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = QuizService(db)
    return await service.get_score(current_user.id)


@router.get("/progress")
async def get_quiz_progress(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = QuizService(db)
    return await service.get_progress(current_user.id)
