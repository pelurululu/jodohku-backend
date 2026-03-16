"""
JODOHKU.MY — Quiz Routes
30-question psychometric quiz with adaptive branching
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    QuizQuestionResponse, QuizAnswerRequest,
    QuizBatchAnswerRequest, PsychometricScoreResponse
)
from app.services.quiz_service import QuizService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/quiz", tags=["Psychometric Quiz"])


@router.get("/questions")
async def get_quiz_questions(
    batch: str = "core",  # "core" (first 10) or "extended" (remaining 20)
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get quiz questions for current batch.
    - Core batch (10 questions): unlocks Bilik Pameran
    - Extended batch (20 questions): improves matching accuracy
    - AI-adaptive: answer patterns influence next questions
    """
    service = QuizService(db)
    questions = await service.get_questions(current_user.id, batch)
    return {"questions": questions, "batch": batch}


@router.post("/answer")
async def submit_answer(
    request: QuizAnswerRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit single quiz answer.
    Returns next question (adaptive branching) and progress.
    """
    service = QuizService(db)
    result = await service.submit_answer(
        current_user.id,
        request.question_id,
        request.score,
        request.time_taken_seconds,
    )
    return {
        "saved": True,
        "next_question": result.get("next_question"),
        "progress": result["progress"],
        "gallery_unlocked": result.get("gallery_unlocked", False),
    }


@router.post("/answers/batch")
async def submit_batch_answers(
    request: QuizBatchAnswerRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit multiple quiz answers at once."""
    service = QuizService(db)
    result = await service.submit_batch(current_user.id, request.answers)
    return result


@router.get("/score", response_model=PsychometricScoreResponse)
async def get_my_score(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's psychometric score breakdown."""
    service = QuizService(db)
    return await service.get_score(current_user.id)


@router.get("/progress")
async def get_quiz_progress(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get quiz completion progress.
    Shows which domains are answered and remaining questions.
    """
    service = QuizService(db)
    return await service.get_progress(current_user.id)
