from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "visiomap.db"
    openrouter_api_key: str = ""
    llm_model: str = "google/gemini-2.0-flash-001"  # free, supports vision
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def use_real_analysis(self) -> bool:
        return bool(self.openrouter_api_key)

    model_config = {"env_file": ".env", "env_prefix": "VISIOMAP_"}


settings = Settings()

# Fallback: use OPENROUTER_API_KEY if VISIOMAP_OPENROUTER_API_KEY not set
if not settings.openrouter_api_key:
    settings.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
