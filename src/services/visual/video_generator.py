from __future__ import annotations

import asyncio
import base64
import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import get_settings
from src.core.interfaces import VideoGenerator as VideoGeneratorABC
from src.core.models import VisualAsset, ChannelType
from src.core.exceptions import VideoGenerationError


KenBurnsEffect = Literal["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]


CHANNEL_MOTION_PRESETS: dict[ChannelType, dict[str, Any]] = {
    ChannelType.HORROR: {
        "motion_prompts": ["slow dramatic zoom", "eerie camera movement", "suspenseful reveal"],
        "default_effect": "zoom_in",
        "speed": 0.8,
    },
    ChannelType.FACTS: {
        "motion_prompts": ["smooth professional pan", "clean zoom transition", "educational reveal"],
        "default_effect": "pan_right",
        "speed": 1.0,
    },
    ChannelType.FINANCE: {
        "motion_prompts": ["corporate camera movement", "professional zoom", "business-like transition"],
        "default_effect": "zoom_out",
        "speed": 0.9,
    },
}


class VideoGenerator(VideoGeneratorABC):
    RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"

    def __init__(self) -> None:
        self.settings = get_settings()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=600.0)
        return self._http_client

    def _get_ffmpeg_path(self) -> str:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise VideoGenerationError("FFmpeg not found in PATH")
        return ffmpeg

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
        reraise=True,
    )
    async def _generate_runway_gen3(
        self,
        image_path: Path,
        motion_prompt: str,
        duration: float,
        output_path: Path,
        **kwargs: Any,
    ) -> VisualAsset:
        client = await self._get_http_client()
        headers = {
            "Authorization": f"Bearer {self.settings.visual.runway_api_key.get_secret_value()}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06",
        }

        image_bytes = image_path.read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode()
        image_uri = f"data:image/png;base64,{image_b64}"

        create_payload = {
            "promptImage": image_uri,
            "promptText": motion_prompt,
            "model": "gen3a_turbo",
            "duration": min(int(duration), 10),
            "ratio": "16:9",
        }

        create_response = await client.post(
            f"{self.RUNWAY_API_BASE}/image_to_video",
            headers=headers,
            json=create_payload,
        )
        create_response.raise_for_status()
        task_id = create_response.json()["id"]

        max_polls = 120
        for _ in range(max_polls):
            await asyncio.sleep(5)
            status_response = await client.get(
                f"{self.RUNWAY_API_BASE}/tasks/{task_id}",
                headers=headers,
            )
            status_response.raise_for_status()
            status_data = status_response.json()

            if status_data["status"] == "SUCCEEDED":
                video_url = status_data["output"][0]
                video_response = await client.get(video_url)
                video_response.raise_for_status()

                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(video_response.content)

                return VisualAsset(
                    asset_type="video",
                    path=output_path,
                    prompt=motion_prompt,
                    duration=duration,
                    metadata={
                        "task_id": task_id,
                        "source_image": str(image_path),
                        "width": 1920,
                        "height": 1080,
                        "provider": "runway_gen3",
                    },
                )
            elif status_data["status"] == "FAILED":
                raise VideoGenerationError(f"Runway Gen-3 failed: {status_data.get('failure', 'Unknown error')}")

        raise VideoGenerationError("Runway Gen-3 timed out")

    async def _generate_ffmpeg_ken_burns(
        self,
        image_path: Path,
        duration: float,
        output_path: Path,
        effect: KenBurnsEffect = "zoom_in",
        **kwargs: Any,
    ) -> VisualAsset:
        ffmpeg = self._get_ffmpeg_path()
        fps = kwargs.get("fps", 30)
        width = kwargs.get("width", 1920)
        height = kwargs.get("height", 1080)
        dur_int = int(duration)

        zoom_effects = {
            "zoom_in": f"scale=8000:-1,zoompan=z='min(zoom+0.001,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fps*dur_int}:s={width}x{height}:fps={fps}",
            "zoom_out": f"scale=8000:-1,zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.001))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fps*dur_int}:s={width}x{height}:fps={fps}",
            "pan_left": f"scale=8000:-1,zoompan=z='1.2':x='iw/2-(iw/zoom/2)+((iw/zoom/2)*({fps*dur_int}-on)/{fps*dur_int})':y='ih/2-(ih/zoom/2)':d={fps*dur_int}:s={width}x{height}:fps={fps}",
            "pan_right": f"scale=8000:-1,zoompan=z='1.2':x='(iw/zoom/2)+(iw/zoom/2)*on/{fps*dur_int}':y='ih/2-(ih/zoom/2)':d={fps*dur_int}:s={width}x{height}:fps={fps}",
            "pan_up": f"scale=8000:-1,zoompan=z='1.2':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+((ih/zoom/2)*({fps*dur_int}-on)/{fps*dur_int})':d={fps*dur_int}:s={width}x{height}:fps={fps}",
            "pan_down": f"scale=8000:-1,zoompan=z='1.2':x='iw/2-(iw/zoom/2)':y='(ih/zoom/2)+(ih/zoom/2)*on/{fps*dur_int}':d={fps*dur_int}:s={width}x{height}:fps={fps}",
        }

        filter_complex = zoom_effects.get(effect, zoom_effects["zoom_in"])

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            ffmpeg,
            "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-vf", filter_complex,
            "-t", str(dur_int),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise VideoGenerationError(f"FFmpeg Ken Burns failed: {stderr.decode()}")

        return VisualAsset(
            asset_type="video",
            path=output_path,
            prompt=f"ken_burns_{effect}",
            duration=duration,
            metadata={
                "effect": effect,
                "source_image": str(image_path),
                "width": width,
                "height": height,
                "provider": "ffmpeg_ken_burns",
            },
        )

    async def generate_from_image(
        self,
        image_path: Path | str,
        motion_prompt: str,
        duration: float,
        output_path: Path | str,
        **kwargs: Any,
    ) -> VisualAsset:
        image_path = Path(image_path)
        output_path = Path(output_path)
        channel_type: ChannelType | None = kwargs.get("channel_type")

        if not image_path.exists():
            raise VideoGenerationError(f"Source image not found: {image_path}")

        try:
            return await self._generate_runway_gen3(
                image_path, motion_prompt, duration, output_path, **kwargs
            )
        except Exception:
            preset = CHANNEL_MOTION_PRESETS.get(
                channel_type if channel_type else ChannelType.FACTS,
                CHANNEL_MOTION_PRESETS[ChannelType.FACTS],
            )
            effect = kwargs.get("fallback_effect", preset["default_effect"])
            return await self._generate_ffmpeg_ken_burns(
                image_path, duration, output_path, effect=effect, **kwargs
            )

    async def generate_batch_from_images(
        self,
        image_paths: list[Path | str],
        motion_prompts: list[str],
        duration: float,
        output_dir: Path | str,
        **kwargs: Any,
    ) -> list[VisualAsset]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if len(motion_prompts) == 1:
            motion_prompts = motion_prompts * len(image_paths)

        tasks = []
        for i, (img_path, prompt) in enumerate(zip(image_paths, motion_prompts)):
            output_path = output_dir / f"video_{i:04d}.mp4"
            tasks.append(
                self.generate_from_image(img_path, prompt, duration, output_path, **kwargs)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assets: list[VisualAsset] = []
        errors: list[str] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Video {i}: {result}")
            elif isinstance(result, VisualAsset):
                assets.append(result)

        if errors and not assets:
            raise VideoGenerationError(f"All batch generations failed: {errors}")

        return assets

    async def concatenate_videos(
        self,
        video_paths: list[Path | str],
        output_path: Path | str,
        **kwargs: Any,
    ) -> VisualAsset:
        ffmpeg = self._get_ffmpeg_path()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        concat_file = output_path.parent / f"concat_{uuid.uuid4().hex[:8]}.txt"
        concat_content = "\n".join(f"file '{Path(p).resolve()}'" for p in video_paths)
        concat_file.write_text(concat_content)

        try:
            cmd = [
                ffmpeg,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-movflags", "+faststart",
                str(output_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _, stderr = await process.communicate()

            if process.returncode != 0:
                raise VideoGenerationError(f"FFmpeg concat failed: {stderr.decode()}")

            total_duration = sum(
                self._get_video_duration(Path(p)) for p in video_paths
            )

            return VisualAsset(
                asset_type="video",
                path=output_path,
                prompt="concatenated_video",
                duration=total_duration,
                metadata={
                    "source_videos": [str(p) for p in video_paths],
                    "width": 1920,
                    "height": 1080,
                    "provider": "ffmpeg_concat",
                },
            )
        finally:
            concat_file.unlink(missing_ok=True)

    def _get_video_duration(self, video_path: Path) -> float:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return 0.0

        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
        return 0.0

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> VideoGenerator:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
