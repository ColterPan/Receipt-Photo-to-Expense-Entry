"""Application settings, loaded from environment variables / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CATEGORIES = (
    "Meals,Travel,Transport,Accommodation,Office Supplies,"
    "Software,Hardware,Entertainment,Utilities,Other"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    expense_file: Path = Path("data/expenses.xlsx")
    archive_dir: Path = Path("data/archive")
    categories: str = DEFAULT_CATEGORIES
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def category_list(self) -> list[str]:
        return [c.strip() for c in self.categories.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
