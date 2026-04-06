from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    APP_ENV: str
    FRONTEND_URL: str

    model_config = ConfigDict(env_file=".env", extra="ignore")


class EmailSettings(BaseSettings):
    RESEND_API_KEY: str
    EMAIL_FROM: str
    RESET_TOKEN_EXPIRE_MINUTES: int

    model_config = ConfigDict(env_file=".env", extra="ignore")


class GoogleSettings(BaseSettings):
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    model_config = ConfigDict(env_file=".env", extra="ignore")


class CloudinarySettings(BaseSettings):
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    model_config = ConfigDict(env_file=".env", extra="ignore")

class StripeSettings(BaseSettings):
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PUBLISHABLE_KEY: str

    model_config = ConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@lru_cache()
def get_email_settings() -> EmailSettings:
    return EmailSettings()


@lru_cache()
def get_google_settings() -> GoogleSettings:
    return GoogleSettings()


@lru_cache()
def get_cloudinary_settings() -> CloudinarySettings:
    return CloudinarySettings()


@lru_cache()
def get_stripe_settings() -> StripeSettings:
    return StripeSettings()
