from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Log Assistant API"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    postgres_db: str = "log_assistant"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    redis_host: str = "redis"
    redis_port: int = 6379
    auth_secret_key: str = "change-this-secret-key"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    upload_dir: str = "assets/uploads"
    max_upload_size: int = 10 * 1024 * 1024
    allowed_extensions: str = ".log,.txt"
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


settings = Settings()
