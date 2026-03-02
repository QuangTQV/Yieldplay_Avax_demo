from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/wordle_season"
    YIELDPLAY_BASE_URL: str = "http://localhost:8001"
    PARTICIPATION_FEE_RATIO: float = 0.02  # 2% of stake

    class Config:
        env_file = ".env"


settings = Settings()
