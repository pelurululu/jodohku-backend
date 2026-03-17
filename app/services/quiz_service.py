"""
JODOHKU.MY — Quiz Service
Real implementation: fetch questions, save answers, compute psychometric score
"""
import uuid
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quiz import QuizQuestion, QuizResponse, PsychometricScore, QuizDomain


# 30 default questions seeded into DB
DEFAULT_QUESTIONS = [
    # Stress Management (3 questions)
    {"domain": "stress_management", "text_ms": "Apabila saya menghadapi tekanan, saya cenderung untuk...", "text_en": "When facing stress, I tend to...", "seq": 1, "is_core": True},
    {"domain": "stress_management", "text_ms": "Saya dapat menguruskan emosi saya dengan baik dalam situasi sukar.", "text_en": "I manage my emotions well in difficult situations.", "seq": 2, "is_core": True},
    {"domain": "stress_management", "text_ms": "Saya memerlukan masa berseorangan untuk mengisi semula tenaga.", "text_en": "I need alone time to recharge my energy.", "seq": 3, "is_core": False},
    # Communication (3 questions)
    {"domain": "communication", "text_ms": "Saya selesa berbincang tentang perasaan saya secara terbuka.", "text_en": "I am comfortable discussing my feelings openly.", "seq": 4, "is_core": True},
    {"domain": "communication", "text_ms": "Saya lebih suka menyelesaikan konflik secara langsung.", "text_en": "I prefer resolving conflicts directly.", "seq": 5, "is_core": True},
    {"domain": "communication", "text_ms": "Saya mendengar dengan penuh perhatian sebelum memberikan pendapat.", "text_en": "I listen attentively before giving my opinion.", "seq": 6, "is_core": False},
    # Empathy (2 questions)
    {"domain": "empathy", "text_ms": "Saya mudah memahami perasaan orang lain.", "text_en": "I easily understand others' feelings.", "seq": 7, "is_core": True},
    {"domain": "empathy", "text_ms": "Saya mengutamakan keperluan pasangan saya berbanding keperluan sendiri.", "text_en": "I prioritize my partner's needs over my own.", "seq": 8, "is_core": False},
    # Future Planning (3 questions)
    {"domain": "future_planning", "text_ms": "Saya mempunyai rancangan kewangan yang jelas untuk masa depan.", "text_en": "I have a clear financial plan for the future.", "seq": 9, "is_core": True},
    {"domain": "future_planning", "text_ms": "Saya berbincang tentang matlamat jangka panjang dengan orang yang saya sayang.", "text_en": "I discuss long-term goals with my loved ones.", "seq": 10, "is_core": True},
    {"domain": "future_planning", "text_ms": "Saya bersedia membuat pengorbanan untuk mencapai matlamat bersama.", "text_en": "I am willing to make sacrifices to achieve shared goals.", "seq": 11, "is_core": False},
    # Accepting Criticism (2 questions)
    {"domain": "accepting_criticism", "text_ms": "Saya menerima kritikan dengan hati yang terbuka.", "text_en": "I accept criticism with an open heart.", "seq": 12, "is_core": False},
    {"domain": "accepting_criticism", "text_ms": "Saya belajar daripada kesilapan saya dan memperbaiki diri.", "text_en": "I learn from my mistakes and improve myself.", "seq": 13, "is_core": False},
    # Discipline (2 questions)
    {"domain": "discipline", "text_ms": "Saya menepati masa dan menghormati komitmen saya.", "text_en": "I am punctual and respect my commitments.", "seq": 14, "is_core": False},
    {"domain": "discipline", "text_ms": "Saya mengamalkan gaya hidup yang teratur dan berdisiplin.", "text_en": "I practice an organized and disciplined lifestyle.", "seq": 15, "is_core": False},
    # Financial Management (3 questions)
    {"domain": "financial_management", "text_ms": "Saya berbelanja mengikut bajet yang telah ditetapkan.", "text_en": "I spend according to a set budget.", "seq": 16, "is_core": False},
    {"domain": "financial_management", "text_ms": "Saya bersetuju bahawa kewangan rumah tangga harus diuruskan bersama.", "text_en": "I agree that household finances should be managed together.", "seq": 17, "is_core": False},
    {"domain": "financial_management", "text_ms": "Saya menyimpan sebahagian pendapatan saya setiap bulan.", "text_en": "I save a portion of my income every month.", "seq": 18, "is_core": False},
    # Spirituality (3 questions)
    {"domain": "spirituality", "text_ms": "Amalan agama adalah bahagian penting dalam kehidupan harian saya.", "text_en": "Religious practice is an important part of my daily life.", "seq": 19, "is_core": True},
    {"domain": "spirituality", "text_ms": "Saya ingin pasangan saya berkongsi nilai-nilai agama yang sama.", "text_en": "I want my partner to share the same religious values.", "seq": 20, "is_core": True},
    {"domain": "spirituality", "text_ms": "Saya mengutamakan pendidikan agama untuk anak-anak saya.", "text_en": "I prioritize religious education for my children.", "seq": 21, "is_core": False},
    # Cooperation (2 questions)
    {"domain": "cooperation", "text_ms": "Saya bersedia berkompromi dalam perkara yang tidak penting.", "text_en": "I am willing to compromise on unimportant matters.", "seq": 22, "is_core": False},
    {"domain": "cooperation", "text_ms": "Saya percaya keputusan penting harus dibuat bersama-sama.", "text_en": "I believe important decisions should be made together.", "seq": 23, "is_core": False},
    # Forgiveness (2 questions)
    {"domain": "forgiveness", "text_ms": "Saya tidak menyimpan dendam terhadap orang yang menyakiti saya.", "text_en": "I don't hold grudges against those who hurt me.", "seq": 24, "is_core": False},
    {"domain": "forgiveness", "text_ms": "Saya percaya memaafkan adalah tanda kekuatan, bukan kelemahan.", "text_en": "I believe forgiving is a sign of strength, not weakness.", "seq": 25, "is_core": False},
    # Resilience (2 questions)
    {"domain": "resilience", "text_ms": "Saya bangkit semula dengan cepat selepas menghadapi kegagalan.", "text_en": "I recover quickly after facing failure.", "seq": 26, "is_core": False},
    {"domain": "resilience", "text_ms": "Saya percaya setiap cabaran adalah peluang untuk berkembang.", "text_en": "I believe every challenge is an opportunity to grow.", "seq": 27, "is_core": False},
    # Leadership (3 questions)
    {"domain": "leadership", "text_ms": "Saya bersedia mengambil tanggungjawab dalam sesebuah keluarga.", "text_en": "I am ready to take responsibility in a family.", "seq": 28, "is_core": False},
    {"domain": "leadership", "text_ms": "Saya memimpin dengan teladan, bukan dengan perintah.", "text_en": "I lead by example, not by command.", "seq": 29, "is_core": False},
    {"domain": "leadership", "text_ms": "Saya percaya perbincangan adalah asas kepemimpinan yang baik.", "text_en": "I believe discussion is the foundation of good leadership.", "seq": 30, "is_core": False},
]


class QuizService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_questions(self, user_id: UUID, batch: int = 1) -> dict:
        """Get quiz questions. Batch 1 = core 10, batch 2 = remaining 20."""
        # Ensure questions exist in DB
        await self._seed_questions_if_empty()

        # Get already answered question IDs
        answered = await self.db.execute(
            select(QuizResponse.question_id).where(QuizResponse.user_id == user_id)
        )
        answered_ids = {r[0] for r in answered.fetchall()}

        # Get questions
        query = select(QuizQuestion).order_by(QuizQuestion.sequence_number)
        if batch == 1:
            query = query.where(QuizQuestion.is_core == True)
        result = await self.db.execute(query)
        questions = result.scalars().all()

        return {
            "questions": [
                {
                    "id": str(q.id),
                    "domain": q.domain.value,
                    "text_ms": q.text_ms,
                    "text_en": q.text_en,
                    "sequence_number": q.sequence_number,
                    "is_core": q.is_core,
                    "already_answered": q.id in answered_ids,
                }
                for q in questions
            ],
            "total": len(questions),
            "answered": len(answered_ids),
        }

    async def submit_answer(self, user_id: UUID, question_id: UUID, score: int, time_taken: int = None) -> dict:
        # Check if already answered
        existing = await self.db.execute(
            select(QuizResponse).where(
                QuizResponse.user_id == user_id,
                QuizResponse.question_id == question_id
            )
        )
        response = existing.scalar_one_or_none()

        if response:
            response.score = score
            response.time_taken_seconds = time_taken
        else:
            response = QuizResponse(
                user_id=user_id,
                question_id=question_id,
                score=score,
                time_taken_seconds=time_taken,
            )
            self.db.add(response)

        await self.db.flush()
        await self._recalculate_score(user_id)

        return {"success": True, "question_id": str(question_id), "score": score}

    async def submit_batch(self, user_id: UUID, answers: list) -> dict:
        for answer in answers:
            await self.submit_answer(user_id, answer.question_id, answer.score, answer.time_taken_seconds)
        score = await self.get_score(user_id)
        return {"submitted": len(answers), "psychometric_score": score}

    async def get_score(self, user_id: UUID) -> dict:
        result = await self.db.execute(
            select(PsychometricScore).where(PsychometricScore.user_id == user_id)
        )
        score = result.scalar_one_or_none()
        if not score:
            return {"domains": {}, "questions_answered": 0, "confidence": 0.0}

        return {
            "domains": score.domain_scores or {},
            "questions_answered": score.questions_answered,
            "confidence": score.confidence,
            "vector": score.vector,
        }

    async def get_progress(self, user_id: UUID) -> dict:
        total_q = (await self.db.execute(select(func.count()).select_from(QuizQuestion))).scalar() or 30
        answered_q = (await self.db.execute(
            select(func.count()).select_from(QuizResponse).where(QuizResponse.user_id == user_id)
        )).scalar() or 0

        return {
            "total": total_q,
            "answered": answered_q,
            "percentage": round((answered_q / max(total_q, 1)) * 100),
            "gallery_unlocked": answered_q >= 10,
        }

    async def _recalculate_score(self, user_id: UUID):
        """Recalculate psychometric score from all responses."""
        responses = await self.db.execute(
            select(QuizResponse, QuizQuestion)
            .join(QuizQuestion, QuizResponse.question_id == QuizQuestion.id)
            .where(QuizResponse.user_id == user_id)
        )
        rows = responses.fetchall()
        if not rows:
            return

        # Group by domain
        domain_scores = {}
        domain_counts = {}
        for response, question in rows:
            domain = question.domain.value
            score = response.score
            if question.is_reverse_scored:
                score = 6 - score  # Reverse: 1->5, 2->4, etc.

            if domain not in domain_scores:
                domain_scores[domain] = 0
                domain_counts[domain] = 0
            domain_scores[domain] += score
            domain_counts[domain] += 1

        # Normalize to 0-1
        normalized = {}
        vector = []
        for domain in sorted(domain_scores.keys()):
            avg = domain_scores[domain] / domain_counts[domain]
            normalized[domain] = round(avg / 5.0, 4)
            vector.append(normalized[domain])

        # Pad vector to 12 dimensions
        while len(vector) < 12:
            vector.append(0.5)
        vector = vector[:12]

        confidence = min(len(rows) / 30.0, 1.0)

        # Upsert PsychometricScore
        existing = await self.db.execute(
            select(PsychometricScore).where(PsychometricScore.user_id == user_id)
        )
        psych = existing.scalar_one_or_none()
        if psych:
            psych.domain_scores = normalized
            psych.vector = vector
            psych.questions_answered = len(rows)
            psych.confidence = confidence
            psych.computed_at = datetime.utcnow()
        else:
            psych = PsychometricScore(
                user_id=user_id,
                domain_scores=normalized,
                vector=vector,
                questions_answered=len(rows),
                confidence=confidence,
            )
            self.db.add(psych)
        await self.db.flush()

    async def _seed_questions_if_empty(self):
        count = (await self.db.execute(select(func.count()).select_from(QuizQuestion))).scalar()
        if count and count > 0:
            return

        for q in DEFAULT_QUESTIONS:
            question = QuizQuestion(
                domain=QuizDomain(q["domain"]),
                text_ms=q["text_ms"],
                text_en=q["text_en"],
                sequence_number=q["seq"],
                is_core=q["is_core"],
                is_reverse_scored=False,
            )
            self.db.add(question)
        await self.db.flush()
