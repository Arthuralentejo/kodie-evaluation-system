from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
