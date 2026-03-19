"""
JODOHKU.MY — eKYC Service
Graceful stub — eKYC is skipped for now (users activate via OTP).
Real implementation requires CTOS/Jumio integration.
"""
from sqlalchemy.ext.asyncio import AsyncSession


class EKYCService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_verification_session(self, request) -> dict:
        # TODO: Integrate with CTOS or Jumio
        return {
            "url": None,
            "session_id": None,
            "message": "eKYC tidak aktif. Pengguna diaktifkan melalui OTP.",
        }

    async def process_callback(self, data: dict) -> dict:
        return {"status": "skipped"}
