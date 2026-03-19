"""
JODOHKU.MY — Database Seed Script
Seeds tier configurations, quiz questions, and ice breakers.

Run: python -m app.utils.seed
"""

async def run_seed():
    async with async_session() as db:
        await seed_tiers(db)
        await seed_questions(db)
        await seed_icebreakers(db)
        await db.commit()
    print("[Seed] Done.")

import asyncio
import uuid
from app.database import async_session, init_db
from app.models.subscription import TierConfig
from app.models.user import SubscriptionTier
from app.models.quiz import QuizQuestion, QuizDomain
from app.models.chat import IceBreaker


TIER_SEED = [
    {
        "tier": SubscriptionTier.RAHMAH,
        "price_myr": 0.00,
        "duration_days": 7,
        "daily_profile_views": 10,
        "max_concurrent_chats": 3,
        "max_messages_per_chat": 10,
        "whatsapp_requests_per_day": 0,
        "golden_tickets_per_month": 0,
        "has_clear_photos": False,
        "has_whatsapp_access": False,
        "has_priority_search": False,
        "has_invisible_mode": False,
        "has_video_taaruf": False,
        "has_human_matchmaker": False,
        "has_ctos_check": False,
        "has_monthly_report": False,
        "has_ads_free": False,
        "has_beta_features": False,
        "badge_label": "Rahmah",
        "badge_color": "#6B7280",
    },
    {
        "tier": SubscriptionTier.GOLD,
        "price_myr": 39.99,
        "duration_days": 30,
        "daily_profile_views": 30,
        "max_concurrent_chats": 10,
        "max_messages_per_chat": 30,
        "whatsapp_requests_per_day": 3,
        "golden_tickets_per_month": 0,
        "has_clear_photos": True,
        "has_whatsapp_access": True,
        "has_priority_search": False,
        "has_invisible_mode": False,
        "has_video_taaruf": False,
        "has_human_matchmaker": False,
        "has_ctos_check": False,
        "has_monthly_report": False,
        "has_ads_free": True,
        "has_beta_features": False,
        "badge_label": "Gold",
        "badge_color": "#C8A23C",
    },
    {
        "tier": SubscriptionTier.PLATINUM,
        "price_myr": 69.99,
        "duration_days": 60,
        "daily_profile_views": 9999,
        "max_concurrent_chats": 9999,
        "max_messages_per_chat": 9999,
        "whatsapp_requests_per_day": 3,
        "golden_tickets_per_month": 0,
        "has_clear_photos": True,
        "has_whatsapp_access": True,
        "has_priority_search": True,
        "has_invisible_mode": False,
        "has_video_taaruf": True,
        "has_human_matchmaker": False,
        "has_ctos_check": False,
        "has_monthly_report": False,
        "has_ads_free": True,
        "has_beta_features": True,
        "badge_label": "Platinum",
        "badge_color": "#A1A1C7",
    },
    {
        "tier": SubscriptionTier.PREMIUM,
        "price_myr": 101.99,
        "duration_days": 90,
        "daily_profile_views": 9999,
        "max_concurrent_chats": 9999,
        "max_messages_per_chat": 9999,
        "whatsapp_requests_per_day": 5,
        "golden_tickets_per_month": 3,
        "has_clear_photos": True,
        "has_whatsapp_access": True,
        "has_priority_search": True,
        "has_invisible_mode": False,
        "has_video_taaruf": True,
        "has_human_matchmaker": False,
        "has_ctos_check": False,
        "has_monthly_report": True,
        "has_ads_free": True,
        "has_beta_features": True,
        "badge_label": "Premium",
        "badge_color": "#7C3AED",
    },
    {
        "tier": SubscriptionTier.SOVEREIGN,
        "price_myr": 1299.99,
        "duration_days": 30,
        "daily_profile_views": 9999,
        "max_concurrent_chats": 9999,
        "max_messages_per_chat": 9999,
        "whatsapp_requests_per_day": 10,
        "golden_tickets_per_month": 5,
        "has_clear_photos": True,
        "has_whatsapp_access": True,
        "has_priority_search": True,
        "has_invisible_mode": True,
        "has_video_taaruf": True,
        "has_human_matchmaker": True,
        "has_ctos_check": True,
        "has_monthly_report": True,
        "has_ads_free": True,
        "has_beta_features": True,
        "badge_label": "Sovereign",
        "badge_color": "#111114",
    },
]


QUIZ_SEED = [
    # Core questions (1-10) — unlocks gallery
    {"domain": QuizDomain.COMMUNICATION, "seq": 1, "core": True,
     "ms": "Saya lebih suka berbincang secara terbuka apabila ada konflik daripada mendiamkan diri.",
     "en": "I prefer to discuss openly when there is conflict rather than staying silent."},
    {"domain": QuizDomain.EMPATHY, "seq": 2, "core": True,
     "ms": "Saya mudah memahami perasaan orang lain walaupun situasi mereka berbeza dari saya.",
     "en": "I easily understand others' feelings even when their situation differs from mine."},
    {"domain": QuizDomain.STRESS_MANAGEMENT, "seq": 3, "core": True,
     "ms": "Saya kekal tenang dan berfikir dengan jelas apabila menghadapi masalah besar.",
     "en": "I remain calm and think clearly when facing big problems."},
    {"domain": QuizDomain.FUTURE_PLANNING, "seq": 4, "core": True,
     "ms": "Saya mempunyai matlamat hidup yang jelas dan sedang berusaha ke arahnya.",
     "en": "I have clear life goals and am working towards them."},
    {"domain": QuizDomain.ACCEPTING_CRITICISM, "seq": 5, "core": True,
     "ms": "Saya boleh menerima teguran dengan hati terbuka tanpa merasa diserang peribadi.",
     "en": "I can accept criticism with an open heart without feeling personally attacked."},
    {"domain": QuizDomain.DISCIPLINE, "seq": 6, "core": True,
     "ms": "Saya menepati janji dan komitmen walaupun situasi berubah.",
     "en": "I keep my promises and commitments even when circumstances change."},
    {"domain": QuizDomain.FINANCIAL_MANAGEMENT, "seq": 7, "core": True,
     "ms": "Saya mempunyai tabungan dan tidak berbelanja melebihi kemampuan.",
     "en": "I have savings and don't spend beyond my means."},
    {"domain": QuizDomain.SPIRITUALITY, "seq": 8, "core": True,
     "ms": "Amalan agama harian adalah bahagian penting dalam kehidupan saya.",
     "en": "Daily religious practice is an important part of my life."},
    {"domain": QuizDomain.COOPERATION, "seq": 9, "core": True,
     "ms": "Saya selesa berkongsi tanggungjawab rumah tangga secara adil dengan pasangan.",
     "en": "I'm comfortable sharing household responsibilities fairly with a partner."},
    {"domain": QuizDomain.FORGIVENESS, "seq": 10, "core": True,
     "ms": "Saya tidak memendam dendam dan boleh memaafkan walaupun terluka.",
     "en": "I don't hold grudges and can forgive even when hurt."},
    # Extended questions (11-30)
    {"domain": QuizDomain.RESILIENCE, "seq": 11, "core": False,
     "ms": "Apabila gagal, saya bangun semula dan cuba dengan pendekatan berbeza.",
     "en": "When I fail, I get back up and try with a different approach."},
    {"domain": QuizDomain.LEADERSHIP, "seq": 12, "core": False,
     "ms": "Dalam perbincangan kumpulan, saya sering mengambil inisiatif untuk membuat keputusan.",
     "en": "In group discussions, I often take initiative to make decisions."},
    {"domain": QuizDomain.COMMUNICATION, "seq": 13, "core": False,
     "ms": "Saya mampu menyatakan perasaan saya dengan jelas tanpa menyalahkan orang lain.",
     "en": "I can express my feelings clearly without blaming others."},
    {"domain": QuizDomain.EMPATHY, "seq": 14, "core": False,
     "ms": "Saya mengambil berat tentang kesejahteraan orang di sekeliling saya.",
     "en": "I care about the wellbeing of people around me."},
    {"domain": QuizDomain.STRESS_MANAGEMENT, "seq": 15, "core": False,
     "ms": "Saya mempunyai cara sihat untuk menguruskan tekanan (senaman, meditasi, hobi).",
     "en": "I have healthy ways to manage stress (exercise, meditation, hobbies)."},
    {"domain": QuizDomain.FUTURE_PLANNING, "seq": 16, "core": False,
     "ms": "Saya merancang kewangan jangka panjang termasuk persaraan dan kecemasan.",
     "en": "I plan finances long-term including retirement and emergencies."},
    {"domain": QuizDomain.DISCIPLINE, "seq": 17, "core": False,
     "ms": "Saya mempunyai rutin harian yang konsisten dan teratur.",
     "en": "I have a consistent and organized daily routine."},
    {"domain": QuizDomain.FINANCIAL_MANAGEMENT, "seq": 18, "core": False,
     "ms": "Saya boleh berbincang tentang wang secara terbuka tanpa rasa malu.",
     "en": "I can discuss money openly without feeling embarrassed."},
    {"domain": QuizDomain.SPIRITUALITY, "seq": 19, "core": False,
     "ms": "Saya berusaha memperbaiki diri dari segi rohani secara berterusan.",
     "en": "I strive to continuously improve myself spiritually."},
    {"domain": QuizDomain.COOPERATION, "seq": 20, "core": False,
     "ms": "Saya sanggup berkompromi untuk kebaikan bersama dalam hubungan.",
     "en": "I'm willing to compromise for mutual benefit in a relationship."},
    {"domain": QuizDomain.FORGIVENESS, "seq": 21, "core": False,
     "ms": "Saya percaya setiap orang layak diberi peluang kedua.",
     "en": "I believe everyone deserves a second chance."},
    {"domain": QuizDomain.RESILIENCE, "seq": 22, "core": False,
     "ms": "Saya melihat cabaran sebagai peluang untuk berkembang.",
     "en": "I see challenges as opportunities to grow."},
    {"domain": QuizDomain.LEADERSHIP, "seq": 23, "core": False,
     "ms": "Saya selesa membuat keputusan penting tanpa bergantung sepenuhnya kepada orang lain.",
     "en": "I'm comfortable making important decisions without fully depending on others."},
    {"domain": QuizDomain.COMMUNICATION, "seq": 24, "core": False,
     "ms": "Saya mendengar untuk memahami, bukan sekadar menunggu giliran untuk bercakap.",
     "en": "I listen to understand, not just to wait for my turn to speak."},
    {"domain": QuizDomain.ACCEPTING_CRITICISM, "seq": 25, "core": False,
     "ms": "Saya menggunakan maklum balas negatif sebagai motivasi untuk memperbaiki diri.",
     "en": "I use negative feedback as motivation to improve myself."},
    {"domain": QuizDomain.EMPATHY, "seq": 26, "core": False,
     "ms": "Saya sanggup mengorbankan keselesaan sendiri untuk membantu orang yang memerlukan.",
     "en": "I'm willing to sacrifice my own comfort to help those in need."},
    {"domain": QuizDomain.COOPERATION, "seq": 27, "core": False,
     "ms": "Saya percaya keputusan besar harus dibuat bersama-sama dengan pasangan.",
     "en": "I believe major decisions should be made together with a partner."},
    {"domain": QuizDomain.FINANCIAL_MANAGEMENT, "seq": 28, "core": False,
     "ms": "Saya boleh membezakan antara keperluan dan kehendak dalam perbelanjaan.",
     "en": "I can distinguish between needs and wants in spending."},
    {"domain": QuizDomain.SPIRITUALITY, "seq": 29, "core": False,
     "ms": "Saya percaya ujian hidup ada hikmah di sebaliknya.",
     "en": "I believe life's tests have wisdom behind them."},
    {"domain": QuizDomain.RESILIENCE, "seq": 30, "core": False,
     "ms": "Saya tidak mudah berputus asa walaupun dalam situasi yang sangat sukar.",
     "en": "I don't easily give up even in very difficult situations."},
]


ICEBREAKER_SEED = [
    {"ms": "Assalamualaikum! Apa yang buat anda tertarik untuk mendaftar di Jodohku?", "en": "Assalamualaikum! What made you interested in joining Jodohku?", "cat": "introduction"},
    {"ms": "Saya perasan kita serasi dari segi komunikasi. Apa pendapat anda?", "en": "I noticed we're compatible in communication style. What do you think?", "cat": "compatibility"},
    {"ms": "Apa matlamat hidup yang paling penting untuk anda capai dalam 5 tahun akan datang?", "en": "What's the most important life goal you want to achieve in the next 5 years?", "cat": "future"},
    {"ms": "Kalau boleh pergi mana-mana di dunia, ke mana anda akan pergi?", "en": "If you could go anywhere in the world, where would you go?", "cat": "lifestyle"},
    {"ms": "Apa buku atau artikel yang paling memberi kesan kepada hidup anda?", "en": "What book or article has had the most impact on your life?", "cat": "intellectual"},
    {"ms": "Bagaimana anda menghabiskan hujung minggu biasanya?", "en": "How do you usually spend your weekends?", "cat": "lifestyle"},
    {"ms": "Apa sifat yang anda paling hargai dalam seorang sahabat?", "en": "What quality do you value most in a friend?", "cat": "values"},
    {"ms": "Apa cara anda untuk kekal positif semasa menghadapi tekanan?", "en": "What's your way of staying positive during stressful times?", "cat": "personality"},
    {"ms": "Apa hobi yang anda ingin cuba tapi belum berkesempatan?", "en": "What hobby do you want to try but haven't had the chance yet?", "cat": "hobbies"},
    {"ms": "Apa tradisi keluarga yang paling bermakna untuk anda?", "en": "What family tradition is most meaningful to you?", "cat": "family"},
]


async def seed_all():
    await init_db()
    async with async_session() as session:
        # Seed Tiers
        for tier_data in TIER_SEED:
            session.add(TierConfig(**tier_data))
        print(f"✓ Seeded {len(TIER_SEED)} tier configurations")

        # Seed Quiz Questions
        for q in QUIZ_SEED:
            session.add(QuizQuestion(
                domain=q["domain"],
                text_ms=q["ms"],
                text_en=q["en"],
                sequence_number=q["seq"],
                is_core=q["core"],
            ))
        print(f"✓ Seeded {len(QUIZ_SEED)} quiz questions")

        # Seed Ice Breakers
        for i, ib in enumerate(ICEBREAKER_SEED):
            session.add(IceBreaker(
                text_ms=ib["ms"],
                text_en=ib["en"],
                category=ib["cat"],
                sort_order=i,
            ))
        print(f"✓ Seeded {len(ICEBREAKER_SEED)} ice breakers")

        await session.commit()
        print("\n✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_all())
