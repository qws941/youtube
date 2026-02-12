"""YouTube Automation Configuration System."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class TTSProvider(StrEnum):
    ELEVENLABS = "elevenlabs"
    EDGE_TTS = "edge_tts"


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="")

    # OpenCode OAuth integration (reads from ~/.local/share/opencode/auth.json)
    use_opencode_auth: bool = True

    # Optional - empty string allowed for DRY_RUN mode or when using OpenCode auth
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))
    openai_api_key: SecretStr = Field(default=SecretStr(""))

    default_provider: LLMProvider = LLMProvider.ANTHROPIC
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o"

    max_retries: int = 3
    timeout: int = 120


class TTSSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ELEVENLABS_")

    # Optional - empty string allowed for DRY_RUN mode
    api_key: SecretStr = Field(default=SecretStr(""))
    voice_horror: str = ""
    voice_facts: str = ""
    voice_finance: str = ""

    default_provider: TTSProvider = TTSProvider.ELEVENLABS
    model: str = "eleven_multilingual_v2"
    stability: float = 0.5
    similarity_boost: float = 0.75


class VisualSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="")

    replicate_api_token: SecretStr = Field(default=SecretStr(""))
    midjourney_api_key: SecretStr = Field(default=SecretStr(""))
    runway_api_key: SecretStr = Field(default=SecretStr(""))

    image_model: str = "stability-ai/sdxl"
    video_model: str = "runway/gen3"

    default_aspect_ratio: str = "16:9"
    thumbnail_size: tuple[int, int] = (1280, 720)


class MusicSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SUNO_")

    api_key: SecretStr = Field(default=SecretStr(""))
    default_duration: int = 180
    instrumental_only: bool = True


class YouTubeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YOUTUBE_")

    client_secrets_file: Path = Path("config/client_secrets.json")
    token_file: Path = Path("config/youtube_token.json")

    channel_horror: str = ""
    channel_facts: str = ""
    channel_finance: str = ""

    default_privacy: Literal["public", "private", "unlisted"] = "private"
    notify_subscribers: bool = True

    @field_validator("client_secrets_file", "token_file", mode="before")
    @classmethod
    def resolve_path(cls, v: str | Path) -> Path:
        return Path(v).resolve()


class ScheduleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHEDULE_")

    horror: str = "0 18 * * 1,3,5"
    facts: str = "0 18 * * 2,4,6"
    finance: str = "0 9 * * *"

    timezone: str = "Asia/Seoul"


class PathSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="")

    output_dir: Path = Path("data/output")
    assets_dir: Path = Path("data/assets")
    templates_dir: Path = Path("data/templates")

    @field_validator("output_dir", "assets_dir", "templates_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()


class FeatureFlags(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ENABLE_")

    thumbnail_ab_test: bool = True
    multilang: bool = False
    dry_run: bool = Field(default=False, validation_alias="DRY_RUN")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm: LLMSettings = Field(default_factory=LLMSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    visual: VisualSettings = Field(default_factory=VisualSettings)
    music: MusicSettings = Field(default_factory=MusicSettings)
    youtube: YouTubeSettings = Field(default_factory=YouTubeSettings)
    schedule: ScheduleSettings = Field(default_factory=ScheduleSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    global _settings
    _settings = Settings()
    return _settings
