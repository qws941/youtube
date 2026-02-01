from pathlib import Path
from typing import Optional, Any, TYPE_CHECKING
import subprocess
import shutil
import tempfile
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from config import get_settings
from src.core.exceptions import VideoCompositionError, FFmpegError
from src.services.video.subtitles import SubtitleGenerator, SubtitleStyle
from src.services.video.music import MusicMixer

if TYPE_CHECKING:
    from src.core.models import VideoProject, Script, AudioSegment, VisualAsset


class VideoComposer:
    OUTPUT_WIDTH = 1920
    OUTPUT_HEIGHT = 1080
    OUTPUT_FPS = 60
    VIDEO_CODEC = "libx264"
    AUDIO_CODEC = "aac"
    AUDIO_BITRATE = "256k"
    VIDEO_BITRATE = "8M"
    CRF = 18
    PRESET = "medium"
    FADE_DURATION = 0.5

    def __init__(self) -> None:
        settings = get_settings()
        self.output_dir = Path(settings.output_dir)
        self.temp_dir = Path(getattr(settings, "temp_dir", "/tmp"))
        self._ffmpeg = shutil.which("ffmpeg")
        self._ffprobe = shutil.which("ffprobe")
        self.subtitle_generator = SubtitleGenerator()
        self.music_mixer = MusicMixer()
        self._executor = ThreadPoolExecutor(max_workers=4)

        if not self._ffmpeg:
            raise VideoCompositionError("ffmpeg not found in PATH")

    async def compose(self, project: Any, output_path: Path) -> Path:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._compose_sync,
            project,
            output_path,
        )

    async def add_subtitles(
        self,
        video_path: Path,
        script: Any,
        output_path: Path,
        style: Optional[dict] = None,
    ) -> Path:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._add_subtitles_sync,
            video_path,
            script,
            output_path,
            style,
        )

    def _compose_sync(self, project: Any, output_path: Path) -> Path:
        with tempfile.TemporaryDirectory(dir=self.temp_dir) as temp:
            temp_path = Path(temp)

            visuals = self._get_visuals(project)
            audio_segments = self._get_audio_segments(project)
            channel_type = self._get_channel_type(project)

            visual_clips = self._prepare_visual_clips(visuals, temp_path)
            concatenated = self._concatenate_clips(visual_clips, temp_path / "concat.mp4")
            scaled = self._scale_video(concatenated, temp_path / "scaled.mp4")

            main_audio = self._prepare_audio(audio_segments, temp_path)

            if channel_type:
                video_duration = self._get_duration(scaled)
                bg_music = self.music_mixer.prepare_background_music(
                    channel_type,
                    video_duration,
                    temp_path / "bg_music.aac",
                )
                if bg_music and main_audio:
                    final_audio = self.music_mixer.mix_with_main_audio(
                        main_audio,
                        bg_music,
                        temp_path / "mixed_audio.aac",
                    )
                else:
                    final_audio = main_audio
            else:
                final_audio = main_audio

            if final_audio:
                combined = self._combine_audio_video(scaled, final_audio, temp_path / "combined.mp4")
            else:
                combined = scaled

            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(combined, output_path)

        return output_path

    def _add_subtitles_sync(
        self,
        video_path: Path,
        script: Any,
        output_path: Path,
        style: Optional[dict] = None,
    ) -> Path:
        with tempfile.TemporaryDirectory(dir=self.temp_dir) as temp:
            temp_path = Path(temp)
            srt_path = temp_path / "subtitles.srt"

            self.subtitle_generator.generate_srt(script, srt_path)
            filter_str = SubtitleStyle.get_ffmpeg_args(srt_path, style)

            output_path.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                self._ffmpeg,
                "-y",
                "-i", str(video_path),
                "-vf", filter_str,
                "-c:v", self.VIDEO_CODEC,
                "-crf", str(self.CRF),
                "-preset", self.PRESET,
                "-c:a", "copy",
                str(output_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise FFmpegError(f"Subtitle burn failed: {result.stderr}")

        return output_path

    def add_subtitles_from_srt(
        self,
        video_path: Path,
        srt_path: Path,
        output_path: Path,
        style: Optional[dict] = None,
    ) -> Path:
        filter_str = SubtitleStyle.get_ffmpeg_args(srt_path, style)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self._ffmpeg,
            "-y",
            "-i", str(video_path),
            "-vf", filter_str,
            "-c:v", self.VIDEO_CODEC,
            "-crf", str(self.CRF),
            "-preset", self.PRESET,
            "-c:a", "copy",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Subtitle burn failed: {result.stderr}")

        return output_path

    def _get_visuals(self, project: Any) -> list[Any]:
        for attr in ("visuals", "visual_assets", "assets", "clips"):
            if hasattr(project, attr):
                val = getattr(project, attr)
                if val:
                    return list(val)
        return []

    def _get_audio_segments(self, project: Any) -> list[Any]:
        for attr in ("audio_segments", "audio", "audio_tracks"):
            if hasattr(project, attr):
                val = getattr(project, attr)
                if val:
                    return list(val)
        return []

    def _get_channel_type(self, project: Any) -> Optional[str]:
        for attr in ("channel_type", "channel", "niche"):
            if hasattr(project, attr):
                val = getattr(project, attr)
                if val:
                    return str(val)
        return None

    def _prepare_visual_clips(
        self,
        visuals: list[Any],
        temp_dir: Path,
    ) -> list[Path]:
        prepared: list[Path] = []

        for i, visual in enumerate(visuals):
            output_clip = temp_dir / f"clip_{i:03d}.mp4"

            asset_type = getattr(visual, "asset_type", getattr(visual, "type", "image"))
            if asset_type == "video":
                clip = self._prepare_video_clip(visual, output_clip)
            else:
                duration = float(getattr(visual, "duration", 5.0))
                visual_path = self._get_path(visual)
                clip = self._image_to_video(visual_path, output_clip, duration)

            prepared.append(clip)

        return prepared

    def _get_path(self, obj: Any) -> Path:
        for attr in ("path", "file_path", "filepath", "url"):
            if hasattr(obj, attr):
                val = getattr(obj, attr)
                if val:
                    return Path(str(val))
        if isinstance(obj, (str, Path)):
            return Path(obj)
        raise VideoCompositionError(f"Cannot extract path from {type(obj)}")

    def _prepare_video_clip(self, visual: Any, output_path: Path) -> Path:
        visual_path = self._get_path(visual)
        duration = getattr(visual, "duration", None)

        cmd = [
            self._ffmpeg,
            "-y",
            "-i", str(visual_path),
        ]
        if duration:
            cmd.extend(["-t", str(duration)])

        cmd.extend([
            "-c:v", self.VIDEO_CODEC,
            "-crf", str(self.CRF),
            "-preset", "fast",
            "-an",
            str(output_path),
        ])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Video prep failed: {result.stderr}")

        return output_path

    def _image_to_video(
        self,
        image_path: Path,
        output_path: Path,
        duration: float,
    ) -> Path:
        zoom_filter = (
            f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
            f"zoompan=z='min(zoom+0.0005,1.1)':d={int(duration * self.OUTPUT_FPS)}:s={self.OUTPUT_WIDTH}x{self.OUTPUT_HEIGHT}"
        )

        cmd = [
            self._ffmpeg,
            "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-vf", zoom_filter,
            "-t", str(duration),
            "-c:v", self.VIDEO_CODEC,
            "-crf", str(self.CRF),
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-r", str(self.OUTPUT_FPS),
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Image to video failed: {result.stderr}")

        return output_path

    def _concatenate_clips(
        self,
        clips: list[Path],
        output_path: Path,
    ) -> Path:
        if not clips:
            raise VideoCompositionError("No clips to concatenate")

        if len(clips) == 1:
            shutil.copy2(clips[0], output_path)
            return output_path

        concat_file = output_path.parent / "concat_list.txt"
        with open(concat_file, "w") as f:
            for clip in clips:
                f.write(f"file '{clip}'\n")

        cmd = [
            self._ffmpeg,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", self.VIDEO_CODEC,
            "-crf", str(self.CRF),
            "-preset", "fast",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Concatenation failed: {result.stderr}")

        return output_path

    def _scale_video(self, input_path: Path, output_path: Path) -> Path:
        cmd = [
            self._ffmpeg,
            "-y",
            "-i", str(input_path),
            "-vf", f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
                   f"pad={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", self.VIDEO_CODEC,
            "-crf", str(self.CRF),
            "-preset", "fast",
            "-r", str(self.OUTPUT_FPS),
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Scale failed: {result.stderr}")

        return output_path

    def _prepare_audio(
        self,
        segments: list[Any],
        temp_dir: Path,
    ) -> Optional[Path]:
        if not segments:
            return None

        if len(segments) == 1:
            return self._get_path(segments[0])

        concat_file = temp_dir / "audio_concat.txt"
        with open(concat_file, "w") as f:
            for seg in segments:
                seg_path = self._get_path(seg)
                f.write(f"file '{seg_path}'\n")

        output_path = temp_dir / "merged_audio.aac"

        cmd = [
            self._ffmpeg,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", self.AUDIO_CODEC,
            "-b:a", self.AUDIO_BITRATE,
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Audio merge failed: {result.stderr}")

        return output_path

    def _combine_audio_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> Path:
        cmd = [
            self._ffmpeg,
            "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", self.AUDIO_CODEC,
            "-b:a", self.AUDIO_BITRATE,
            "-shortest",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"AV combine failed: {result.stderr}")

        return output_path

    def _get_duration(self, video_path: Path) -> float:
        cmd = [
            self._ffprobe,
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "json",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def create_preview(
        self,
        video_path: Path,
        output_path: Path,
        max_duration: float = 30.0,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self._ffmpeg,
            "-y",
            "-i", str(video_path),
            "-t", str(max_duration),
            "-c:v", self.VIDEO_CODEC,
            "-crf", "28",
            "-preset", "fast",
            "-c:a", self.AUDIO_CODEC,
            "-b:a", "128k",
            "-vf", "scale=854:480",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Preview creation failed: {result.stderr}")

        return output_path
