from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "mysql+pymysql://eventmer:eventmer@localhost:3306/eventmer?charset=utf8mb4"
    # Conteúdo PEM do certificado da CA do banco (ex.: Aiven). Vazio = sem SSL.
    database_ssl_ca: str = ""

    jwt_secret: str = "dev-only-jwt-secret-change-me-0123456789"
    jwt_algorithm: str = "HS256"
    qr_secret: str = "dev-only-qr-secret-change-me-0123456789"
    access_token_minutes: int = 15
    refresh_token_days: int = 14

    # E-mail: "console" (só imprime no log), "smtp" ou "gmail_api"
    email_backend: str = "console"
    email_from_address: str = ""
    email_from_name: str = "EVENTMER"
    email_reply_to: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""  # senha de app do Google
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""

    cors_origins: list[str] = ["http://localhost:3000"]
    frontend_url: str = "http://localhost:3000"
    timezone: str = "America/Sao_Paulo"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and (
        settings.jwt_secret.startswith("dev-only") or settings.qr_secret.startswith("dev-only")
    ):
        raise RuntimeError("JWT_SECRET e QR_SECRET precisam ser definidos em produção.")
    return settings
