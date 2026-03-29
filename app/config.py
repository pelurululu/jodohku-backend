"""
JODOHKU.MY — Application Configuration
Centralized settings management using pydantic-settings
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──
    app_name: str = "Jodohku.my"
    app_version: str = "2.0.0"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "change-this-in-production"
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # ── Database ──
    database_url: str = "postgresql+asyncpg://localhost/jodohku_db"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # ── JWT ──
    jwt_secret_key: str = "change-this-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    # ── Brevo Email API ──
    brevo_api_key: str = ""
    brevo_sender_email: str = "noreply@jodohku.my"
    brevo_sender_name: str = "Jodohku.my"

    # ── ToyyibPay ──
    toyyibpay_secret_key: str = ""
    toyyibpay_category_code: str = ""
    toyyibpay_base_url: str = "https://toyyibpay.com"
    toyyibpay_callback_url: str = ""

    # ── Billplz (Failover) ──
    billplz_api_key: str = ""
    billplz_collection_id: str = ""
    billplz_base_url: str = "https://www.billplz-sandbox.com/api/v3"

    # ── SenangPay (Failover) ──
    senangpay_merchant_id: str = ""
    senangpay_secret_key: str = ""

    # ── e-KYC (Jumio) ──
    ekyc_api_key: str = ""
    ekyc_api_secret: str = ""
    ekyc_base_url: str = "https://netverify.com/api/v4"

    # ── Liveness Detection (iProov) ──
    iproov_api_key: str = ""
    iproov_secret: str = ""
    iproov_base_url: str = "https://eu.rp.secure.iproov.me/api/v2"

    # ── CTOS ──
    ctos_api_key: str = ""
    ctos_base_url: str = "https://api.ctos.com.my"

    # ── Firebase ──
    fcm_server_key: str = ""
    fcm_project_id: str = ""

    # ── WhatsApp Business API ──
    whatsapp_api_url: str = "https://graph.facebook.com/v18.0"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # ── Sentry ──
    sentry_dsn: str = ""

    # ── File Upload ──
    max_image_size_mb: int = 10
    allowed_image_types: str = "image/jpeg,image/png,image/webp"
    upload_dir: str = "/var/jodohku/uploads"

    # ── Rate Limiting ──
    rate_limit_per_minute: int = 60
    rate_limit_login_per_minute: int = 5

    # ── Business Logic ──
    daily_candidates: int = 5
    daily_reset_hour: int = 8
    free_msg_limit: int = 10
    pioneer_quota: int = 3000
    pioneer_trial_days: int = 7

    # ── URLs ──
    frontend_url: str = "https://jodohku.my"
    backend_url: str = "https://api.jodohku.my"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
