from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # protected_namespaces=() — разрешаем поля с префиксом model_ (model_name и т.д.)
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),
    )

    postgres_user: str = "sentiment_user"
    postgres_password: str = "sentiment_pass"
    postgres_db: str = "sentiment_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_host: str = "redis"
    redis_port: int = 6379

    model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"
    model_max_length: int = 512

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
