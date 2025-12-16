from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    - extra="ignore" нужен, чтобы POSTGRES_DB/USER/PASSWORD (и другие переменные)
      не валили worker/app, даже если мы их не используем напрямую в коде
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # убираем конфликт с protected namespace "model_"
        protected_namespaces=("settings_",),
    )

    # DB
    database_url: str = Field(
        default="postgresql+psycopg://clarus:clarus_password@database:5432/clarus",
        alias="DATABASE_URL",
    )

    # Auth/JWT
    jwt_secret_key: str = Field(default="CHANGE_ME", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # RabbitMQ
    rabbitmq_url: str = Field(default="amqp://guest:guest@rabbitmq:5672/", alias="RABBITMQ_URL")
    ml_queue_name: str = Field(default="ml_jobs", alias="ML_QUEUE_NAME")

    # Paths
    model_dir: str = Field(default="/data/models", alias="MODEL_DIR")
    uploads_dir: str = Field(default="/data/uploads", alias="UPLOADS_DIR")

    # Models (XGBoost)
    xgb_bin_path: str = Field(default="/data/models/xgb_bin.json", alias="XGB_BIN_PATH")
    xgb_multi_path: str = Field(default="/data/models/xgb_multi.json", alias="XGB_MULTI_PATH")

    xgb_class_mapping_path: str = Field(default="/data/models/class_mapping.json", alias="XGB_CLASS_MAPPING_PATH")
    xgb_features_bin_path: str = Field(default="/data/models/features_bin.json", alias="XGB_FEATURES_BIN_PATH")
    xgb_features_multi_path: str = Field(default="/data/models/features_multi.json", alias="XGB_FEATURES_MULTI_PATH")


settings = Settings()
