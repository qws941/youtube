import contextlib
import json
import random
import shutil
import subprocess
from pathlib import Path

from config import get_settings
from src.core.exceptions import FFmpegError


class MusicMixer:
    CHANNEL_MUSIC_MAP = {
        "horror": ["dark_ambient", "tension", "horror"],
        "facts": ["corporate", "upbeat", "inspiring"],
        "finance": ["corporate", "professional", "news"],
    }

    DEFAULT_VOLUME = 0.18
    FADE_DURATION = 2.0

    def __init__(self, music_dir: Path | None = None):
        settings = get_settings()
        self.music_dir = music_dir or Path(settings.assets_dir) / "music"
        self._ffmpeg = shutil.which("ffmpeg")
        self._ffprobe = shutil.which("ffprobe")

    def select_music(
        self,
        channel_type: str,
        mood: str | None = None,
    ) -> Path | None:
        categories = self.CHANNEL_MUSIC_MAP.get(channel_type, ["ambient"])
        if mood:
            categories = [mood] + categories

        for category in categories:
            category_dir = self.music_dir / category
            if category_dir.exists():
                music_files = list(category_dir.glob("*.mp3")) + list(category_dir.glob("*.wav"))
                if music_files:
                    return random.choice(music_files)

        all_music = list(self.music_dir.rglob("*.mp3")) + list(self.music_dir.rglob("*.wav"))
        return random.choice(all_music) if all_music else None

    def get_duration(self, audio_path: Path) -> float:
        if not self._ffprobe:
            raise FFmpegError("ffprobe not found")

        cmd = [
            self._ffprobe,
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "json",
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def loop_to_duration(
        self,
        music_path: Path,
        target_duration: float,
        output_path: Path,
    ) -> Path:
        if not self._ffmpeg:
            raise FFmpegError("ffmpeg not found")

        music_duration = self.get_duration(music_path)
        loop_count = int(target_duration / music_duration) + 1

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self._ffmpeg,
            "-y",
            "-stream_loop", str(loop_count),
            "-i", str(music_path),
            "-t", str(target_duration),
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Loop failed: {result.stderr}")

        return output_path

    def normalize_volume(
        self,
        audio_path: Path,
        output_path: Path,
        target_loudness: float = -16.0,
    ) -> Path:
        if not self._ffmpeg:
            raise FFmpegError("ffmpeg not found")

        analyze_cmd = [
            self._ffmpeg,
            "-i", str(audio_path),
            "-af", "loudnorm=print_format=json",
            "-f", "null",
            "-",
        ]
        result = subprocess.run(analyze_cmd, capture_output=True, text=True)

        measured_i = -23.0
        measured_tp = -1.0
        measured_lra = 7.0
        measured_thresh = -34.0

        for line in result.stderr.split("\n"):
            if '"input_i"' in line:
                with contextlib.suppress(ValueError, IndexError):
                    measured_i = float(line.split(":")[1].strip().strip('",'))
            elif '"input_tp"' in line:
                with contextlib.suppress(ValueError, IndexError):
                    measured_tp = float(line.split(":")[1].strip().strip('",'))

        output_path.parent.mkdir(parents=True, exist_ok=True)

        normalize_cmd = [
            self._ffmpeg,
            "-y",
            "-i", str(audio_path),
            "-af", (
                f"loudnorm=I={target_loudness}:TP=-1.5:LRA=11:"
                f"measured_I={measured_i}:measured_TP={measured_tp}:"
                f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:linear=true"
            ),
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ]

        result = subprocess.run(normalize_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Normalization failed: {result.stderr}")

        return output_path

    def mix_with_main_audio(
        self,
        main_audio: Path,
        music_path: Path,
        output_path: Path,
        music_volume: float = DEFAULT_VOLUME,
        fade_in: float = FADE_DURATION,
        fade_out: float = FADE_DURATION,
    ) -> Path:
        if not self._ffmpeg:
            raise FFmpegError("ffmpeg not found")

        main_duration = self.get_duration(main_audio)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        filter_complex = (
            f"[1:a]volume={music_volume},"
            f"afade=t=in:st=0:d={fade_in},"
            f"afade=t=out:st={main_duration - fade_out}:d={fade_out}[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[out]"
        )

        cmd = [
            self._ffmpeg,
            "-y",
            "-i", str(main_audio),
            "-i", str(music_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "aac",
            "-b:a", "256k",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(f"Mixing failed: {result.stderr}")

        return output_path

    def prepare_background_music(
        self,
        channel_type: str,
        target_duration: float,
        output_path: Path,
        mood: str | None = None,
    ) -> Path | None:
        music_file = self.select_music(channel_type, mood)
        if not music_file:
            return None

        looped_path = output_path.parent / f"looped_{output_path.name}"
        looped = self.loop_to_duration(music_file, target_duration, looped_path)

        normalized = self.normalize_volume(looped, output_path)

        if looped_path.exists() and looped_path != output_path:
            looped_path.unlink()

        return normalized
