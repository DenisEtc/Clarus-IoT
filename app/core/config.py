from __future__ import annotations

from typing import Optional

from pydantic import Field, AliasChoices, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings.

    Supports both:
      - DATABASE_URL / JWT_SECRET_KEY (single variables)
    and a split docker-compose style:
      - POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_HOST/POSTGRES_PORT/POSTGRES_DB
      - JWT_SECRET
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    postgres_user: str = Field(
        default="clarus",
        validation_alias=AliasChoices("POSTGRES_USER"),
    )
    postgres_password: str = Field(
        default="clarus",
        validation_alias=AliasChoices("POSTGRES_PASSWORD"),
    )
    postgres_host: str = Field(
        default="database",
        validation_alias=AliasChoices("POSTGRES_HOST"),
    )
    postgres_port: int = Field(
        default=5432,
        validation_alias=AliasChoices("POSTGRES_PORT"),
    )
    postgres_db: str = Field(
        default="clarus",
        validation_alias=AliasChoices("POSTGRES_DB"),
    )

    # JWT
    jwt_secret_key: str = Field(
        default="CHANGE_ME_SUPER_SECRET",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET", "jwt_secret_key"),
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "jwt_algorithm"),
    )
    access_token_expire_minutes: int = Field(
        default=60,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES", "access_token_expire_minutes"),
    )

    @model_validator(mode="after")
    def _assemble_database_url(self) -> "Settings":
        if not self.database_url:
            self.database_url = (
                f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return self


settings = Settings()
