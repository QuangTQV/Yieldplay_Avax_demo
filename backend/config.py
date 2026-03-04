from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/wordle_season"
    YIELDPLAY_BASE_URL: str = "http://host.docker.internal:8088"
    PARTICIPATION_FEE_RATIO: float = 0.02
    YIELDPLAY_GAME_ID: str = ""  # bytes32 hex, tạo qua POST /games khi deploy  # 2% of stake
    YIELDPLAY_API_KEY: str = ""
    GAME_TREASURY_ADDRESS: str = "0xf971eEFd58b0831C9868A1a25A49D7EfD279D9c5"
    YIELDPLAY_TOKEN_ADDRESS: str = "0x1C5dB89a642e39F6dC79BEDfa76029af17FE3A04"
    YIELDPLAY_API_PREFIX: str = "/api/v1"

    class Config:
        env_file = ".env"


settings = Settings()
