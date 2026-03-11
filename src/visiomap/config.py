from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_path: str = "visiomap.db"
    openai_api_key: str = ""
    debug: bool = False
    max_batch_size: int = 50


settings = Settings()
