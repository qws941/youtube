from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


class ChannelType(StrEnum):
    HORROR = "horror"
    FACTS = "facts"
    FINANCE = "finance"


class ContentStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    UPLOADED = "uploaded"


class VideoStyle(StrEnum):
    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    STORYTELLING = "storytelling"
    EDUCATIONAL = "educational"
    NEWS = "news"


@dataclass
class Script:
    title: str
    hook: str
    body: str
    cta: str
    channel: ChannelType

    id: UUID = field(default_factory=uuid4)
    keywords: list[str] = field(default_factory=list)
    emotion_markers: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    estimated_duration: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def full_text(self) -> str:
        return f"{self.hook}\n\n{self.body}\n\n{self.cta}"

    @property
    def word_count(self) -> int:
        return len(self.full_text.split())


@dataclass
class AudioSegment:
    path: Path
    duration: float
    text: str
    start_time: float = 0.0
    voice_id: str = ""


@dataclass
class VisualAsset:
    path: Path
    asset_type: str
    duration: float = 0.0
    prompt: str = ""
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Thumbnail:
    path: Path
    title_text: str
    variant: str = "A"
    ctr_score: float = 0.0


@dataclass
class VideoProject:
    id: UUID
    channel: ChannelType
    script: Script
    status: ContentStatus = ContentStatus.PENDING

    audio_segments: list[AudioSegment] = field(default_factory=list)
    visual_assets: list[VisualAsset] = field(default_factory=list)
    background_music: Path | None = None
    thumbnails: list[Thumbnail] = field(default_factory=list)

    output_path: Path | None = None
    youtube_id: str | None = None
    scheduled_at: datetime | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None

    @classmethod
    def create(cls, channel: ChannelType, script: Script) -> VideoProject:
        return cls(
            id=uuid4(),
            channel=channel,
            script=script,
        )

    def mark_failed(self, error: str) -> None:
        self.status = ContentStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(UTC)

    def mark_completed(self, output_path: Path) -> None:
        self.status = ContentStatus.COMPLETED
        self.output_path = output_path
        self.updated_at = datetime.now(UTC)


@dataclass
class ChannelConfig:
    channel_type: ChannelType
    name: str
    youtube_channel_id: str
    voice_id: str

    upload_schedule: str
    target_duration: tuple[int, int] = (480, 600)
    style: VideoStyle = VideoStyle.STORYTELLING

    topics: list[str] = field(default_factory=list)
    banned_topics: list[str] = field(default_factory=list)
    thumbnail_style: str = "dramatic"

    hashtags: list[str] = field(default_factory=list)
    default_tags: list[str] = field(default_factory=list)


CHANNEL_CONFIGS: dict[ChannelType, ChannelConfig] = {
    ChannelType.HORROR: ChannelConfig(
        channel_type=ChannelType.HORROR,
        name="Dark Tales",
        youtube_channel_id="",
        voice_id="",
        upload_schedule="0 18 * * 1,3,5",
        target_duration=(480, 720),
        style=VideoStyle.STORYTELLING,
        topics=[
            "unexplained mysteries",
            "creepy stories",
            "paranormal events",
            "urban legends",
            "true crime mysteries",
        ],
        banned_topics=["gore", "suicide", "self-harm", "child abuse"],
        thumbnail_style="dark_dramatic",
        hashtags=["horror", "creepy", "scary", "mystery", "paranormal"],
        default_tags=["horror stories", "scary stories", "creepypasta", "true scary stories"],
    ),
    ChannelType.FACTS: ChannelConfig(
        channel_type=ChannelType.FACTS,
        name="Mind Blown Facts",
        youtube_channel_id="",
        voice_id="",
        upload_schedule="0 18 * * 2,4,6",
        target_duration=(300, 480),
        style=VideoStyle.EDUCATIONAL,
        topics=[
            "science facts",
            "psychology facts",
            "history mysteries",
            "space exploration",
            "human body",
        ],
        banned_topics=["misinformation", "conspiracy theories"],
        thumbnail_style="bright_curious",
        hashtags=["facts", "science", "education", "mindblown", "didyouknow"],
        default_tags=["facts", "amazing facts", "science facts", "education"],
    ),
    ChannelType.FINANCE: ChannelConfig(
        channel_type=ChannelType.FINANCE,
        name="Wealth Insights",
        youtube_channel_id="",
        voice_id="",
        upload_schedule="0 9 * * *",
        target_duration=(300, 600),
        style=VideoStyle.EDUCATIONAL,
        topics=[
            "investing strategies",
            "passive income",
            "stock market",
            "real estate",
            "crypto basics",
            "financial independence",
        ],
        banned_topics=["get rich quick", "gambling", "pump and dump"],
        thumbnail_style="professional_money",
        hashtags=["finance", "investing", "money", "wealth", "passiveincome"],
        default_tags=["personal finance", "investing", "money tips", "financial freedom"],
    ),
}
