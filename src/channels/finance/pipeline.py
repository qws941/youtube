"""Finance channel content pipeline."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from src.channels.finance.prompts import (
    DESCRIPTION_TEMPLATE,
    DISCLAIMER_TEXT,
    FORBIDDEN_TOPICS,
    SCRIPT_TEMPLATE,
    TAGS_GENERATION,
    TITLE_OPTIMIZATION,
    TOPIC_GENERATION,
    VISUAL_PROMPT_TEMPLATE,
)
from src.core.exceptions import PipelineError
from src.core.interfaces import ContentPipeline
from src.core.models import (
    CHANNEL_CONFIGS,
    ChannelType,
    Script,
    VideoProject,
)

if TYPE_CHECKING:
    from src.core.interfaces import (
        ImageGenerator,
        ScriptGenerator,
        ThumbnailGenerator,
        TTSEngine,
        VideoComposer,
        VideoGenerator,
        YouTubeUploader,
    )

logger = getLogger(__name__)


@runtime_checkable
class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str: ...


class FinancePipeline(ContentPipeline):
    """Pipeline for finance/wealth education content."""

    channel_type = ChannelType.FINANCE

    def __init__(
        self,
        script_generator: ScriptGenerator,
        tts_engine: TTSEngine,
        image_generator: ImageGenerator,
        video_generator: VideoGenerator,
        video_composer: VideoComposer,
        thumbnail_generator: ThumbnailGenerator,
        youtube_uploader: YouTubeUploader,
        output_base: Path | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.script_generator = script_generator
        self.tts_engine = tts_engine
        self.image_generator = image_generator
        self.video_generator = video_generator
        self.video_composer = video_composer
        self.thumbnail_generator = thumbnail_generator
        self.youtube_uploader = youtube_uploader
        self.config = CHANNEL_CONFIGS.get(ChannelType.FINANCE, {})
        self.output_base = output_base or Path("data/output")
        self._llm_client = llm_client

    async def run(self, channel: ChannelType) -> VideoProject:
        """Run single video generation pipeline."""
        project_id = uuid.uuid4()
        topic = await self._generate_topic()
        script = await self._build_script(topic)
        output_path = self.output_base / str(project_id)
        output_path.mkdir(parents=True, exist_ok=True)

        project = VideoProject(
            id=project_id,
            channel=ChannelType.FINANCE,
            script=script,
            output_path=output_path,
        )
        logger.info("finance_pipeline_start project_id=%s", project_id)

        try:
            self._validate_script(script)
            audio_path = await self._generate_audio(output_path, script)
            visuals = await self._generate_visuals(output_path, script)
            video_path = await self._compose_video(
                project, output_path, audio_path, visuals, script
            )
            thumbnails = await self._generate_thumbnails(output_path, topic)
            await self._upload_video(project, video_path, thumbnails, script, topic)
            project.mark_completed(output_path)
            logger.info("finance_pipeline_complete project_id=%s", project_id)
        except PipelineError:
            raise
        except Exception as e:
            logger.error("finance_pipeline_failed project_id=%s error=%s", project_id, e)
            project.mark_failed(error=str(e))
            raise PipelineError(f"Finance pipeline failed: {e}") from e

        return project

    async def run_batch(self, channel: ChannelType, count: int) -> AsyncIterator[VideoProject]:
        """Run batch video generation."""
        topics = await self._generate_topics_batch(count)
        for topic in topics:
            project_id = uuid.uuid4()
            script = await self._build_script(topic)
            output_path = self.output_base / str(project_id)
            output_path.mkdir(parents=True, exist_ok=True)

            project = VideoProject(
                id=project_id,
                channel=ChannelType.FINANCE,
                script=script,
                output_path=output_path,
            )
            logger.info(
                "finance_batch_item_start project_id=%s topic=%s", project_id, topic.get("title")
            )
            try:
                self._validate_script(script)
                audio_path = await self._generate_audio(output_path, script)
                visuals = await self._generate_visuals(output_path, script)
                video_path = await self._compose_video(
                    project, output_path, audio_path, visuals, script
                )
                thumbnails = await self._generate_thumbnails(output_path, topic)
                await self._upload_video(project, video_path, thumbnails, script, topic)
                project.mark_completed(output_path)
            except Exception as e:
                logger.error("finance_batch_item_failed project_id=%s error=%s", project_id, e)
                project.mark_failed(error=str(e))
            yield project

    # Topic generation
    async def _generate_topic(self) -> dict[str, Any]:
        prompt = TOPIC_GENERATION.format(count=1)
        response = await self._llm_generate(prompt)
        topics = self._parse_json_response(response)
        if not topics:
            raise PipelineError("No topics generated")
        return topics[0] if isinstance(topics, list) else topics

    async def _generate_topics_batch(self, count: int) -> list[dict[str, Any]]:
        prompt = TOPIC_GENERATION.format(count=count)
        response = await self._llm_generate(prompt)
        topics = self._parse_json_response(response)
        if not topics:
            raise PipelineError("No topics generated")
        return topics[:count] if isinstance(topics, list) else [topics]

    # Script building
    async def _build_script(self, topic: dict[str, Any]) -> Script:
        duration = self._cfg("target_duration_minutes", 8)
        prompt = SCRIPT_TEMPLATE.format(
            duration_minutes=duration,
            topic=topic.get("title", ""),
            hook=topic.get("hook", ""),
            category=topic.get("category", "investing"),
        )
        body = await self._llm_generate(prompt)

        # Ensure disclaimer is in script
        if "educational purposes" not in body.lower():
            body = body + "\n\n" + DISCLAIMER_TEXT.strip()

        title_variants = await self._generate_title_variants(topic)
        title = title_variants[0] if title_variants else topic.get("title", "Untitled")

        return Script(
            title=title,
            hook=topic.get("hook", body[:100] if body else ""),
            body=body,
            cta="Subscribe for more wealth-building insights!",
            channel=ChannelType.FINANCE,
        )

    async def _generate_title_variants(self, topic: dict[str, Any]) -> list[str]:
        prompt = TITLE_OPTIMIZATION.format(
            original_title=topic.get("title", ""),
            topic=topic.get("title", ""),
        )
        try:
            response = await self._llm_generate(prompt)
            variants = self._parse_json_response(response)
            return variants if isinstance(variants, list) else [topic.get("title", "Untitled")]
        except Exception:
            return [topic.get("title", "Untitled")]

    async def _generate_description(self, topic: dict[str, Any], script_content: str) -> str:
        key_points = script_content[:500].replace("\n", " ")
        prompt = DESCRIPTION_TEMPLATE.format(
            title=topic.get("title", ""),
            topic=topic.get("title", ""),
            key_points=key_points,
            keywords=", ".join(topic.get("keywords", [])),
        )
        description = await self._llm_generate(prompt)
        # Always add disclaimer to description
        if "educational purposes" not in description.lower():
            description = description + "\n\n" + DISCLAIMER_TEXT.strip()
        return description

    async def _generate_tags(self, topic: dict[str, Any]) -> list[str]:
        prompt = TAGS_GENERATION.format(
            title=topic.get("title", ""),
            category=topic.get("category", "finance"),
            keywords=", ".join(topic.get("keywords", [])),
        )
        response = await self._llm_generate(prompt)
        return [tag.strip() for tag in response.split(",") if tag.strip()]

    def _validate_script(self, script: Script) -> None:
        """Validate script content - extra strict for finance."""
        content = script.body.lower()

        # Check forbidden topics
        for forbidden in FORBIDDEN_TOPICS:
            if forbidden in content:
                raise PipelineError(f"Script contains forbidden topic: {forbidden}")

        # Finance-specific validation
        red_flags = [
            "guaranteed",
            "100%",
            "risk-free",
            "can't lose",
            "sure thing",
            "secret method",
            "millionaire overnight",
        ]
        for flag in red_flags:
            if flag in content:
                logger.warning("finance_script_warning: contains '%s' - review recommended", flag)

        # Word count validation (finance videos slightly shorter)
        wc = script.word_count
        if wc < 1000:
            raise PipelineError(f"Script too short: {wc} words (min: 1000)")
        if wc > 1800:
            raise PipelineError(f"Script too long: {wc} words (max: 1800)")

        if not script.title or len(script.title) > 100:
            raise PipelineError("Invalid title length")

    # Audio generation
    async def _generate_audio(self, output_path: Path, script: Script) -> Path:
        clean_script = self._clean_script_for_tts(script.body)
        audio_file = output_path / "audio.mp3"
        voice_id = self._cfg("voice_id", "default")
        await self.tts_engine.synthesize(
            text=clean_script,
            output_path=audio_file,
            voice_id=voice_id,
        )
        return audio_file

    def _clean_script_for_tts(self, content: str) -> str:
        """Remove markers for TTS."""
        content = re.sub(r"\[CONFIDENT\]", "", content)
        content = re.sub(r"\[SERIOUS\]", "", content)
        content = re.sub(r"\[ENCOURAGING\]", "", content)
        content = re.sub(r"\[.*?\]", "", content)
        return content.strip()

    # Visual generation
    async def _generate_visuals(self, output_path: Path, script: Script) -> list[Path]:
        scenes = self._extract_scenes(script)
        visual_paths: list[Path] = []

        for i, scene in enumerate(scenes):
            prompt = VISUAL_PROMPT_TEMPLATE.format(
                scene_description=scene["description"],
                mood=scene.get("mood", "professional, trustworthy"),
                timestamp=scene.get("timestamp", f"{i * 30}s"),
            )
            image_file = output_path / f"visual_{i:03d}.png"
            await self.image_generator.generate(prompt=prompt, output_path=image_file)

            video_file = output_path / f"clip_{i:03d}.mp4"
            duration = scene.get("duration", 5)
            await self._create_video_clip(image_file, video_file, duration)
            visual_paths.append(video_file)

        return visual_paths

    async def _create_video_clip(self, image_path: Path, output_path: Path, duration: int) -> None:
        motion_prompt = "professional slow zoom with subtle motion"
        await self.video_generator.generate_from_image(
            image_path=image_path,
            motion_prompt=motion_prompt,
            duration=float(duration),
            output_path=output_path,
        )

    def _extract_scenes(self, script: Script) -> list[dict[str, Any]]:
        """Extract scenes from script paragraphs."""
        paragraphs = [p.strip() for p in script.body.split("\n\n") if p.strip()]
        scenes: list[dict[str, Any]] = []
        est_dur = (script.word_count / 160) * 60  # 160 WPM for professional tone
        dur_per = est_dur / max(len(paragraphs), 1)

        for i, para in enumerate(paragraphs):
            # Mood detection for finance content
            if any(w in para.lower() for w in ["mistake", "wrong", "lose", "risk"]):
                mood = "serious, cautionary"
            elif any(w in para.lower() for w in ["grow", "wealth", "success", "freedom"]):
                mood = "aspirational, optimistic"
            else:
                mood = "professional, educational"

            scenes.append(
                {
                    "description": para[:200],
                    "mood": mood,
                    "timestamp": f"{int(i * dur_per)}s",
                    "duration": max(3, min(8, int(dur_per))),
                }
            )
        return scenes[:15]  # Max 15 scenes

    # Video composition
    async def _compose_video(
        self,
        project: VideoProject,
        output_path: Path,
        audio_path: Path,
        visual_paths: list[Path],
        script: Script,
    ) -> Path:
        video_file = output_path / "final.mp4"
        composer = self.video_composer
        if hasattr(composer, "compose"):
            await composer.compose(project=project, output_path=video_file)
        return video_file

    # Thumbnail generation
    async def _generate_thumbnails(self, output_path: Path, topic: dict[str, Any]) -> list[Path]:
        thumbnails: list[Path] = []
        for variant in range(3):
            thumb_file = output_path / f"thumbnail_{variant}.png"
            await self.thumbnail_generator.generate(
                title=topic.get("title", "")[:40],
                channel=ChannelType.FINANCE,
                output_path=thumb_file,
            )
            thumbnails.append(thumb_file)
        return thumbnails

    # Upload
    async def _upload_video(
        self,
        project: VideoProject,
        video_path: Path,
        thumbnails: list[Path],
        script: Script,
        topic: dict[str, Any],
    ) -> None:
        offset_hours = self._cfg("schedule_offset_hours", 24)
        schedule_time = datetime.now(UTC) + timedelta(hours=offset_hours)
        description = await self._generate_description(topic, script.body)
        tags = await self._generate_tags(topic)

        uploader = self.youtube_uploader
        if hasattr(uploader, "upload"):
            await uploader.upload(
                video_path=video_path,
                title=script.title,
                description=description,
                tags=tags,
                thumbnail_path=thumbnails[0] if thumbnails else None,
                scheduled_at=schedule_time.isoformat() if schedule_time else None,
            )
        logger.info("finance_video_uploaded project_id=%s", project.id)

    # Helpers
    async def _llm_generate(self, prompt: str) -> str:
        if self._llm_client is not None:
            return await self._llm_client.generate(prompt)
        gen = self.script_generator
        if hasattr(gen, "_llm_generate"):
            return await gen._llm_generate(prompt)  # type: ignore[attr-defined]
        if hasattr(gen, "client") and hasattr(gen.client, "generate"):  # type: ignore[attr-defined]
            return await gen.client.generate(prompt)  # type: ignore[attr-defined]
        raise PipelineError("No LLM client available for raw text generation")

    def _cfg(self, key: str, default: Any) -> Any:
        if isinstance(self.config, dict):
            return self.config.get(key, default)
        return getattr(self.config, key, default)

    def _parse_json_response(self, response: str) -> list[Any] | dict[str, Any]:
        response = response.strip()
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if json_match:
            response = json_match.group(1).strip()
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            array_match = re.search(r"\[[\s\S]*\]", response)
            if array_match:
                return json.loads(array_match.group())
            obj_match = re.search(r"\{[\s\S]*\}", response)
            if obj_match:
                return json.loads(obj_match.group())
            raise PipelineError(f"Failed to parse JSON: {response[:100]}")
