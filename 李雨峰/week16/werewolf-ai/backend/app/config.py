"""Application configuration management."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # LLM Provider
    llm_provider: Literal["openai", "claude", "mock"] = "mock"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "gpt-4o-mini"

    # Claude-specific
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # Game
    max_players_per_room: int = 12
    min_players_to_start: int = 6
    default_speak_time_seconds: int = 30

    # Logging
    log_level: str = "INFO"
    log_dir: Path = Path(__file__).resolve().parent / "data" / "logs"

    @property
    def is_mock_mode(self) -> bool:
        """Return True if LLM calls should use mock/stub responses."""
        return self.llm_provider == "mock"


# Singleton
settings = Settings()
