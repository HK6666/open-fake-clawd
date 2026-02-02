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
    allowed_users: str = ""  # Comma-separated user IDs

    # LLM Provider: claude-cli, anthropic, openai, openrouter
    llm_provider: str = "claude-cli"

    # Claude CLI (default)
    claude_cli_path: str = "claude"
    approved_directory: str = ""
    claude_timeout: int = 600  # Increased from 300 to 600 seconds (10 minutes)
    claude_max_turns: int = 50

    # Anthropic API
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # OpenAI API
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # OpenRouter API
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4"

    # GLM (智谱AI) API
    glm_api_key: str = ""
    glm_model: str = "glm-4.7"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "change_me"

    # Rate Limiting
    rate_limit_requests: int = 10
    rate_limit_window: int = 60

    # Workspace
    workspace_path: str = "./workspace"

    # Database
    database_url: str = "sqlite+aiosqlite:///./workspace/ccbot.db"

    # Logging
    log_level: str = "INFO"

    # Proxy
    proxy_url: str = ""  # http://127.0.0.1:7890 or socks5://127.0.0.1:1080

    # Performance
    max_concurrent_sessions: int = 5  # Max concurrent sessions per user
    session_timeout_minutes: int = 120  # Auto-cleanup after inactivity
    max_message_history: int = 100  # Max messages to keep in session

    # Features
    enable_file_uploads: bool = False  # Allow file uploads (future feature)
    enable_voice_messages: bool = False  # Voice message support (future)
    auto_save_sessions: bool = True  # Auto-save sessions periodically

    @property
    def allowed_users_list(self) -> List[int]:
        """Get allowed users as list of integers."""
        if not self.allowed_users.strip():
            return []
        return [int(uid.strip()) for uid in self.allowed_users.split(",") if uid.strip()]

    @property
    def approved_directory_path(self) -> Path:
        """Get approved directory as Path."""
        if self.approved_directory:
            return Path(self.approved_directory).expanduser().resolve()
        return Path.home() / "projects"

    @property
    def workspace_path_resolved(self) -> Path:
        """Get workspace path as Path."""
        return Path(self.workspace_path).expanduser().resolve()

    @property
    def memory_path(self) -> Path:
        """Path to memory directory."""
        return self.workspace_path_resolved / "memory"

    @property
    def sessions_path(self) -> Path:
        """Path to sessions directory."""
        return self.workspace_path_resolved / "sessions"

    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.workspace_path_resolved.mkdir(parents=True, exist_ok=True)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.sessions_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
