from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = ""

    @property
    def resolved_database_url(self) -> str:
        url = self.DATABASE_URL.strip() if self.DATABASE_URL else ""
        if not url:
            return f"sqlite:///{(BASE_DIR / 'columnlab.db').as_posix()}"
        if url.startswith("sqlite:///./"):
            db_path = BASE_DIR / url.removeprefix("sqlite:///./")
            return f"sqlite:///{db_path.as_posix()}"
        return url
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    STAGING_DIR: str = "staging"
    DATASETS_DIR: str = "datasets"
    CORS_ORIGINS: str = "http://localhost:5173"
    MAX_UPLOAD_MB: int = 512

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def resolve_path(self, relative: str) -> Path:
        path = BASE_DIR / relative
        path.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_storage_dirs(self) -> None:
        for d in (self.STAGING_DIR, self.DATASETS_DIR):
            self.resolve_path(d)


@lru_cache
def get_settings() -> Settings:
    return Settings()
