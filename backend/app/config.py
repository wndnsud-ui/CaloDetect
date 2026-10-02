from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    database_url: str | None = None
    frontend_origin: str = 'http://localhost:5173'
    age_min: int | None = None
    image_storage_dir: str | None = None
    recommendation_enabled: bool = False
    recent_meal_window: int | None = None
    cookie_secure: bool = False
    session_hours: int = 24
    service_consent_text: str | None = None
    model_improvement_consent_text: str | None = None


settings = Settings()
