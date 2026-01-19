"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://attendancems:attendancems@localhost:5432/attendancems"
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES: int = 1440
    SEED_DEMO_DATA: bool = False
    APP_ENV: str = "production"
    FACE_RECOGNITION_TOLERANCE: float = 0.6

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
