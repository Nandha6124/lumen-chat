from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./lumen.db"
    secret_key: str = "dev-only-change-me"
    access_token_minutes: int = 60 * 12
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    max_history_messages: int = 20
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
