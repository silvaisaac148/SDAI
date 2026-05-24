from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    CAPTURE_INTERFACE: str = "Wi-Fi"
    CAPTURE_COUNT: int = 100

    # Notifications — Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Notifications — SMTP/Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SENDER: str = ""
    SMTP_USE_TLS: bool = True
    # Comma-separated list of recipients for SMTP alerts
    EMAIL_RECIPIENTS: str = ""
    # IA Defensiva y Educativa — Google Gemini API
    GEMINI_API_KEY: str = ""
    # IA Defensiva y Educativa — Groq API (openai-compatible)
    GROQ_API_KEY: str = ""

    # Seguridad y Autenticación del Analista (sin JWT, sesión por Cookies HMAC)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    SESSION_SECRET_KEY: str = "sdai_super_secret_session_key_99"
    # Set True behind HTTPS in production so cookies are only sent over TLS.
    SESSION_COOKIE_SECURE: bool = False
    # CORS — comma-separated origins. Defaults wide-open for local dev only.
    CORS_ALLOWED_ORIGINS: str = "*"


settings = Settings()
