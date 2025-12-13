from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    postgres_db: str = "clarus"
    postgres_user: str = "clarus"
    postgres_password: str = "clarus_password"
    postgres_host: str = "database"
    postgres_port: int = 5432

    jwt_secret: str = "change_me"
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 60

    @property
    def database_url(self) -> str:
        # SQLAlchemy URL (psycopg v3)
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

settings = Settings()
