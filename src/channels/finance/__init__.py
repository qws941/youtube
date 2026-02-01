"""Finance channel pipeline and prompts."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.channels.finance.pipeline import FinancePipeline
from src.channels.finance.prompts import (
    FORBIDDEN_TOPICS,
    TOPIC_GENERATION,
    SCRIPT_TEMPLATE,
    VISUAL_PROMPT_TEMPLATE,
    THUMBNAIL_PROMPT_TEMPLATE,
    TITLE_OPTIMIZATION,
    DESCRIPTION_TEMPLATE,
    TAGS_GENERATION,
    DISCLAIMER_TEXT,
)

if TYPE_CHECKING:
    pass


def create_pipeline(output_base: Path | None = None) -> FinancePipeline:
    from src.services import (
        get_script_generator,
        TTSEngineImpl,
        ImageGenerator,
        VideoGenerator,
        VideoComposer,
        ThumbnailGenerator,
        YouTubeUploader,
        get_llm_client,
    )

    return FinancePipeline(
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
    "FinancePipeline",
    "create_pipeline",
    "FORBIDDEN_TOPICS",
    "TOPIC_GENERATION",
    "SCRIPT_TEMPLATE",
    "VISUAL_PROMPT_TEMPLATE",
    "THUMBNAIL_PROMPT_TEMPLATE",
    "TITLE_OPTIMIZATION",
    "DESCRIPTION_TEMPLATE",
    "TAGS_GENERATION",
    "DISCLAIMER_TEXT",
]
