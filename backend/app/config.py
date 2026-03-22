from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/runs.db"
    redis_url: str = "redis://localhost:6379/0"
    data_dir: str = "./data"
    dev_eager: bool = False   # set DEV_EAGER=true to run Celery tasks inline (no Redis needed)
    cors_origins: str = "*"   # comma-separated allowed origins, e.g. http://localhost:5173


settings = Settings()
