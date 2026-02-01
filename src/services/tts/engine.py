from __future__ import annotations

import contextlib
import re
import uuid
from pathlib import Path
from typing import Any, Literal, cast

from config import get_settings
from src.core.exceptions import TTSError, TTSQuotaExceededError
from src.core.models import AudioSegment, ChannelType, Script
from src.services.tts.edge_tts import EdgeTTSClient
from src.services.tts.elevenlabs import ElevenLabsClient

Provider = Literal["elevenlabs", "edge"]

EMOTION_VOICE_SETTINGS: dict[str, dict[str, float]] = {
    "neutral": {"stability": 0.5, "similarity_boost": 0.75},
    "excited": {"stability": 0.3, "similarity_boost": 0.85},
    "sad": {"stability": 0.7, "similarity_boost": 0.6},
    "angry": {"stability": 0.25, "similarity_boost": 0.9},
    "fearful": {"stability": 0.35, "similarity_boost": 0.8},
    "suspenseful": {"stability": 0.6, "similarity_boost": 0.7},
    "serious": {"stability": 0.65, "similarity_boost": 0.7},
    "happy": {"stability": 0.4, "similarity_boost": 0.8},
}

CHANNEL_VOICE_MAP: dict[ChannelType, dict[str, str]] = {
    ChannelType.HORROR: {
        "elevenlabs": "pNInz6obpgDQGcFmaJgB",
        "edge": "en-US-DavisNeural",
    },
    ChannelType.FACTS: {
        "elevenlabs": "21m00Tcm4TlvDq8ikWAM",
        "edge": "en-US-AriaNeural",
    },
    ChannelType.FINANCE: {
        "elevenlabs": "ErXwobaYiN019PkySvjV",
        "edge": "en-US-GuyNeural",
    },
}


class TTSEngineImpl:
    def __init__(
        self,
        prefer_provider: Provider = "elevenlabs",
        output_dir: Path | str | None = None,
        auto_fallback: bool = True,
    ):
        settings = get_settings()
        self._prefer_provider: Provider = prefer_provider
        self._output_dir = Path(output_dir or settings.paths.output_dir / "audio")
        self._auto_fallback = auto_fallback

        self._elevenlabs: ElevenLabsClient | None = None
        self._edge: EdgeTTSClient | None = None

        self._init_clients()

    def _init_clients(self) -> None:
        settings = get_settings()

        if self._prefer_provider == "elevenlabs" and settings.tts.api_key.get_secret_value():
            with contextlib.suppress(Exception):
                self._elevenlabs = ElevenLabsClient()

        self._edge = EdgeTTSClient()

    def synthesize(
        self,
        text: str,
        voice_id: str | None = None,
        output_path: Path | str | None = None,
        channel_type: ChannelType | None = None,
    ) -> AudioSegment:
        if output_path is None:
            output_path = self._output_dir / f"{uuid.uuid4().hex}.mp3"
        output_path = Path(output_path)

        resolved_voice = voice_id or self._get_voice_for_channel(
            channel_type, self._prefer_provider
        )

        if self._prefer_provider == "elevenlabs" and self._elevenlabs:
            try:
                return self._elevenlabs.synthesize(text, resolved_voice, output_path)
            except TTSQuotaExceededError:
                if self._auto_fallback and self._edge:
                    edge_voice = self._get_voice_for_channel(channel_type, cast(Provider, "edge"))
                    return self._edge.synthesize(text, edge_voice, output_path)
                raise
            except TTSError:
                if self._auto_fallback and self._edge:
                    edge_voice = self._get_voice_for_channel(channel_type, cast(Provider, "edge"))
                    return self._edge.synthesize(text, edge_voice, output_path)
                raise

        if self._edge:
            edge_voice = (
                resolved_voice
                if "Neural" in (resolved_voice or "")
                else self._get_voice_for_channel(channel_type, cast(Provider, "edge"))
            )
            return self._edge.synthesize(text, edge_voice, output_path)

        raise TTSError("No TTS provider available")

    def synthesize_with_emotions(
        self,
        text: str,
        voice_id: str | None = None,
        output_path: Path | str | None = None,
        channel_type: ChannelType | None = None,
    ) -> AudioSegment:
        segments = self._parse_emotion_markers(text)

        if len(segments) == 1 and segments[0][0] == "neutral":
            return self.synthesize(segments[0][1], voice_id, output_path, channel_type)

        if output_path is None:
            output_path = self._output_dir / f"{uuid.uuid4().hex}.mp3"
        output_path = Path(output_path)

        temp_files: list[Path] = []
        total_duration = 0.0
        full_text = ""

        try:
            for emotion, segment_text in segments:
                if not segment_text.strip():
                    continue

                temp_path = self._output_dir / f"temp_{uuid.uuid4().hex}.mp3"
                temp_files.append(temp_path)

                segment = self._synthesize_with_emotion(
                    segment_text,
                    emotion,
                    voice_id,
                    temp_path,
                    channel_type,
                )
                total_duration += segment.duration
                full_text += segment_text + " "

            self._concatenate_audio(temp_files, output_path)

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

        resolved_voice = voice_id or self._get_voice_for_channel(
            channel_type, self._prefer_provider
        )

        return AudioSegment(
            path=output_path,
            duration=total_duration,
            text=full_text.strip(),
            start_time=0.0,
            voice_id=resolved_voice,
        )

    def _synthesize_with_emotion(
        self,
        text: str,
        emotion: str,
        voice_id: str | None,
        output_path: Path,
        channel_type: ChannelType | None,
    ) -> AudioSegment:
        settings_map = EMOTION_VOICE_SETTINGS.get(
            emotion.lower(), EMOTION_VOICE_SETTINGS["neutral"]
        )

        resolved_voice = voice_id or self._get_voice_for_channel(
            channel_type, self._prefer_provider
        )

        if self._prefer_provider == "elevenlabs" and self._elevenlabs:
            try:
                return self._elevenlabs.synthesize(
                    text,
                    resolved_voice,
                    output_path,
                    stability=settings_map["stability"],
                    similarity_boost=settings_map["similarity_boost"],
                )
            except (TTSError, TTSQuotaExceededError):
                if self._auto_fallback and self._edge:
                    return self._synthesize_edge_with_emotion(
                        text, emotion, output_path, channel_type
                    )
                raise

        if self._edge:
            return self._synthesize_edge_with_emotion(text, emotion, output_path, channel_type)

        raise TTSError("No TTS provider available")

    def _synthesize_edge_with_emotion(
        self,
        text: str,
        emotion: str,
        output_path: Path,
        channel_type: ChannelType | None,
    ) -> AudioSegment:
        if self._edge is None:
            raise TTSError("Edge TTS client not available")

        edge_voice = self._get_voice_for_channel(channel_type, cast(Provider, "edge"))
        rate = self._edge.adjust_rate_for_emotion(emotion)
        pitch = self._edge.adjust_pitch_for_emotion(emotion)

        return self._edge.synthesize(
            text,
            edge_voice,
            output_path,
            rate=rate,
            pitch=pitch,
        )

    def _parse_emotion_markers(self, text: str) -> list[tuple[str, str]]:
        pattern = r"\[(\w+)\](.*?)(?=\[\w+\]|$)"
        matches = re.findall(pattern, text, re.DOTALL)

        if not matches:
            return [("neutral", text)]

        return [(emotion.lower(), segment.strip()) for emotion, segment in matches]

    def _concatenate_audio(self, files: list[Path], output_path: Path) -> None:
        try:
            from pydub import AudioSegment as PydubAudio
        except ImportError:
            raise TTSError("pydub not installed, cannot concatenate audio")

        if not files:
            raise TTSError("No audio files to concatenate")

        combined = PydubAudio.empty()
        for file in files:
            segment = PydubAudio.from_mp3(file)
            combined += segment

        combined.export(output_path, format="mp3", bitrate="128k")

    def _get_voice_for_channel(self, channel_type: ChannelType | None, provider: Provider) -> str:
        if channel_type is None:
            channel_type = ChannelType.FACTS

        voice_map = CHANNEL_VOICE_MAP.get(channel_type, CHANNEL_VOICE_MAP[ChannelType.FACTS])
        return voice_map[provider]

    def get_available_voices(self, provider: Provider | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {}

        target_provider = provider or self._prefer_provider

        if target_provider == "elevenlabs" and self._elevenlabs:
            try:
                result["elevenlabs"] = self._elevenlabs.get_voices()
            except TTSError:
                result["elevenlabs"] = []

        if target_provider == "edge" or provider is None:
            result["edge"] = {
                "korean": EdgeTTSClient.get_korean_voices(),
                "english": EdgeTTSClient.get_english_voices(),
            }

        return result

    def synthesize_script(
        self,
        script: Script,
        output_dir: Path | str | None = None,
    ) -> list[AudioSegment]:
        output_dir_path = Path(output_dir or self._output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        segments: list[AudioSegment] = []
        current_time = 0.0

        script_scenes: list[Any] = getattr(script, "scenes", [])
        script_channel: ChannelType | None = getattr(script, "channel_type", None)

        for idx, scene in enumerate(script_scenes):
            output_path = output_dir_path / f"scene_{idx:03d}.mp3"

            text = getattr(scene, "voiceover", None) or getattr(scene, "narration", None)
            if not text:
                continue

            segment = self.synthesize_with_emotions(
                text,
                channel_type=script_channel,
                output_path=output_path,
            )

            segment.start_time = current_time
            current_time += segment.duration
            segments.append(segment)

        return segments

    def close(self) -> None:
        if self._elevenlabs:
            self._elevenlabs.close()
