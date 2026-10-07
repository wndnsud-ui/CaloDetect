from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    database_url: str | None = None
    app_env: Literal['development', 'production'] = 'production'
    local_test_signup: bool = False
    local_test_image_analysis: bool = False
    frontend_origin: str = 'http://localhost:5173'
    age_min: int | None = Field(default=18, ge=18, le=120)
    image_storage_dir: str | None = None
    recommendation_enabled: bool = False
    recent_meal_window: int | None = None
    cookie_secure: bool = False
    session_hours: int = 24
    password_reset_secret: str | None = Field(default=None, min_length=32)
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_security: Literal['starttls', 'ssl'] = 'starttls'
    service_consent_text: str | None = None
    model_improvement_consent_text: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = 'http://localhost:8000/api/auth/google/callback'
    apple_client_id: str | None = None
    apple_redirect_uri: str | None = None
    oauth_state_secret: str | None = Field(default=None, min_length=32)


settings = Settings()
