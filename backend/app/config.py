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
    EMAIL_RECIPIENTS: str = ""  # comma-separated


settings = Settings()
