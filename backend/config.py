"""Configuration management using pydantic-settings."""

from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str
    allowed_users: List[int] = []

    # Claude Code
    claude_cli_path: str = "claude"
    approved_directory: Path = Path.home() / "projects"
    claude_timeout: int = 300
    claude_max_turns: int = 50

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "change_me"

    # Rate Limiting
    rate_limit_requests: int = 10
    rate_limit_window: int = 60

    # Workspace
    workspace_path: Path = Path("./workspace")

    # Database
    database_url: str = "sqlite+aiosqlite:///./ccbot.db"

    # Logging
    log_level: str = "INFO"

    @field_validator("allowed_users", mode="before")
    @classmethod
    def parse_allowed_users(cls, v):
        """Parse comma-separated user IDs."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(uid.strip()) for uid in v.split(",") if uid.strip()]
        return v

    @field_validator("approved_directory", "workspace_path", mode="before")
    @classmethod
    def parse_path(cls, v):
        """Convert string to Path."""
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v

    @property
    def memory_path(self) -> Path:
        """Path to memory directory."""
        return self.workspace_path / "memory"

    @property
    def sessions_path(self) -> Path:
        """Path to sessions directory."""
        return self.workspace_path / "sessions"

    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.sessions_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
