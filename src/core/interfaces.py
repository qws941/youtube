from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path

from src.core.models import (
    AudioSegment,
    ChannelType,
    Script,
    Thumbnail,
    VideoProject,
    VisualAsset,
)


class ScriptGenerator(ABC):
    @abstractmethod
    async def generate_topic(self, channel: ChannelType) -> str:
        pass

    @abstractmethod
    async def generate_script(self, topic: str, channel: ChannelType) -> Script:
        pass

    @abstractmethod
    async def validate_script(self, script: Script) -> tuple[bool, list[str]]:
        pass


class TTSEngine(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path,
    ) -> AudioSegment:
        pass

    @abstractmethod
    async def synthesize_with_emotions(
        self,
        script: Script,
        voice_id: str,
        output_dir: Path,
    ) -> list[AudioSegment]:
        pass

    @abstractmethod
    async def get_available_voices(self) -> list[dict]:
        pass


class ImageGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        output_path: Path,
        **kwargs,
    ) -> VisualAsset:
        pass

    @abstractmethod
    async def generate_batch(
        self,
        prompts: list[str],
        output_dir: Path,
    ) -> list[VisualAsset]:
        pass


class VideoGenerator(ABC):
    @abstractmethod
    async def generate_from_image(
        self,
        image_path: Path,
        motion_prompt: str,
        duration: float,
        output_path: Path,
    ) -> VisualAsset:
        pass


class MusicGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        duration: int,
        output_path: Path,
    ) -> Path:
        pass


class VideoComposer(ABC):
    @abstractmethod
    async def compose(
        self,
        project: VideoProject,
        output_path: Path,
    ) -> Path:
        pass

    @abstractmethod
    async def add_subtitles(
        self,
        video_path: Path,
        script: Script,
        output_path: Path,
    ) -> Path:
        pass


class ThumbnailGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        title: str,
        channel: ChannelType,
        output_path: Path,
    ) -> Thumbnail:
        pass

    @abstractmethod
    async def generate_variants(
        self,
        title: str,
        channel: ChannelType,
        output_dir: Path,
        count: int = 3,
    ) -> list[Thumbnail]:
        pass


class YouTubeUploader(ABC):
    @abstractmethod
    async def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        thumbnail_path: Path | None = None,
        scheduled_at: str | None = None,
    ) -> str:
        pass

    @abstractmethod
    async def update_thumbnail(
        self,
        video_id: str,
        thumbnail_path: Path,
    ) -> bool:
        pass

    @abstractmethod
    async def get_analytics(
        self,
        video_id: str,
    ) -> dict:
        pass


class ContentPipeline(ABC):
    @abstractmethod
    async def run(self, channel: ChannelType) -> VideoProject:
        pass

    @abstractmethod
    def run_batch(
        self,
        channel: ChannelType,
        count: int,
    ) -> AsyncIterator[VideoProject]:
        pass
