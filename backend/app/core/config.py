import json
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "kodie-evaluation-backend"
    env: str = "dev"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "kodie"

    jwt_secret: str = "change-me"
    jwt_kid: str = "v1"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 30

    shuffle_seed_version: str = "v1"

    cpf_attempt_limit: int = 5
    ip_attempt_limit: int = 20
    rate_limit_window_minutes: int = 15
    cpf_lock_minutes: int = 30

    cors_allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: list[str] | str) -> list[str]:
        if isinstance(value, list):
            return value

        raw_value = value.strip()
        if not raw_value:
            return []

        if raw_value.startswith("["):
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                bracket_content = raw_value[1:-1].strip()
                if not raw_value.endswith("]"):
                    raise ValueError(f"Invalid CORS_ALLOWED_ORIGINS format: {exc.msg}") from exc
                if not bracket_content:
                    return []
                return [item.strip().strip("\"'") for item in bracket_content.split(",") if item.strip()]
            if not isinstance(parsed, list):
                raise ValueError("cors_allowed_origins must be a JSON array or comma-separated string")
            return [str(item).strip() for item in parsed if str(item).strip()]

        return [item.strip() for item in raw_value.split(",") if item.strip()]


settings = Settings()
