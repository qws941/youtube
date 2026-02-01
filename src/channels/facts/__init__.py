"""Facts channel pipeline and prompts."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.channels.facts.pipeline import FactsPipeline
from src.channels.facts.prompts import (
    DESCRIPTION_TEMPLATE,
    FORBIDDEN_TOPICS,
    SCRIPT_TEMPLATE,
    TAGS_GENERATION,
    THUMBNAIL_PROMPT_TEMPLATE,
    TITLE_OPTIMIZATION,
    TOPIC_GENERATION,
    VISUAL_PROMPT_TEMPLATE,
)

if TYPE_CHECKING:
    pass


def create_pipeline(output_base: Path | None = None) -> FactsPipeline:
    from src.services import (
        ImageGenerator,
        ThumbnailGenerator,
        TTSEngineImpl,
        VideoComposer,
        VideoGenerator,
        YouTubeUploader,
        get_llm_client,
        get_script_generator,
    )

    return FactsPipeline(
        script_generator=get_script_generator(),
        tts_engine=TTSEngineImpl(),  # type: ignore[arg-type]
        image_generator=ImageGenerator(),
        video_generator=VideoGenerator(),
        video_composer=VideoComposer(),  # type: ignore[arg-type]
        thumbnail_generator=ThumbnailGenerator(),
        youtube_uploader=YouTubeUploader(),
        output_base=output_base,
        llm_client=get_llm_client(),
    )


__all__ = [
    "FactsPipeline",
    "create_pipeline",
    "FORBIDDEN_TOPICS",
    "TOPIC_GENERATION",
    "SCRIPT_TEMPLATE",
    "VISUAL_PROMPT_TEMPLATE",
    "THUMBNAIL_PROMPT_TEMPLATE",
    "TITLE_OPTIMIZATION",
    "DESCRIPTION_TEMPLATE",
    "TAGS_GENERATION",
]
