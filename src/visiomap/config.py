from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "visiomap.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def use_real_analysis(self) -> bool:
        return self.openai_api_key is not None

    model_config = {"env_file": ".env", "env_prefix": "VISIOMAP_"}


settings = Settings()
