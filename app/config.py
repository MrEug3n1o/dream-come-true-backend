from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./dreammaker.db"
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    APP_ENV: str

    model_config = ConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


class EmailSettings(BaseSettings):
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str

    SMTP_PASSWORD: str
    EMAIL_FROM: str
    FRONTEND_URL: str
    RESET_TOKEN_EXPIRE_MINUTES: int

    model_config = ConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_email_settings() -> EmailSettings:
    return EmailSettings()
