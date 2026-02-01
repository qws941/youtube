from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal

import edge_tts
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.exceptions import TTSError
from src.core.models import AudioSegment

VoiceGender = Literal["Male", "Female"]

KOREAN_VOICES = {
    "ko-KR-SunHiNeural": {"gender": "Female", "style": "neutral"},
    "ko-KR-InJoonNeural": {"gender": "Male", "style": "neutral"},
    "ko-KR-HyunsuNeural": {"gender": "Male", "style": "narrative"},
    "ko-KR-YuJinNeural": {"gender": "Female", "style": "friendly"},
}

ENGLISH_VOICES = {
    "en-US-GuyNeural": {"gender": "Male", "style": "neutral"},
    "en-US-JennyNeural": {"gender": "Female", "style": "neutral"},
    "en-US-AriaNeural": {"gender": "Female", "style": "narrative"},
    "en-US-DavisNeural": {"gender": "Male", "style": "narrative"},
    "en-US-SaraNeural": {"gender": "Female", "style": "friendly"},
    "en-GB-RyanNeural": {"gender": "Male", "style": "neutral"},
    "en-GB-SoniaNeural": {"gender": "Female", "style": "neutral"},
}


class EdgeTTSClient:
    DEFAULT_VOICE_KO = "ko-KR-SunHiNeural"
    DEFAULT_VOICE_EN = "en-US-GuyNeural"

    def __init__(
        self,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        self._rate = rate
        self._volume = volume
        self._pitch = pitch

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def _synthesize_async(
        self,
        text: str,
        voice: str,
        output_path: Path,
        rate: str | None = None,
        volume: str | None = None,
        pitch: str | None = None,
    ) -> None:
        communicate = edge_tts.Communicate(  # type: ignore[attr-defined]
            text=text,
            voice=voice,
            rate=rate or self._rate,
            volume=volume or self._volume,
            pitch=pitch or self._pitch,
        )
        await communicate.save(str(output_path))

    def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path | str,
        rate: str | None = None,
        volume: str | None = None,
        pitch: str | None = None,
    ) -> AudioSegment:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.ensure_future(
                    self._synthesize_async(text, voice, output_path, rate, volume, pitch)
                )
                loop.run_until_complete(future)
            else:
                asyncio.run(
                    self._synthesize_async(text, voice, output_path, rate, volume, pitch)
                )
        except Exception as e:
            raise TTSError(f"Edge TTS synthesis failed: {e}") from e

        duration = self._get_audio_duration(output_path)

        return AudioSegment(
            path=output_path,
            duration=duration,
            text=text,
            start_time=0.0,
            voice_id=voice,
        )

    async def synthesize_async(
        self,
        text: str,
        voice: str,
        output_path: Path | str,
        rate: str | None = None,
        volume: str | None = None,
        pitch: str | None = None,
    ) -> AudioSegment:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            await self._synthesize_async(text, voice, output_path, rate, volume, pitch)
        except Exception as e:
            raise TTSError(f"Edge TTS synthesis failed: {e}") from e

        duration = self._get_audio_duration(output_path)

        return AudioSegment(
            path=output_path,
            duration=duration,
            text=text,
            start_time=0.0,
            voice_id=voice,
        )

    def _get_audio_duration(self, path: Path) -> float:
        try:
            from mutagen.mp3 import MP3
            audio = MP3(path)
            return audio.info.length
        except Exception:
            return 0.0

    @staticmethod
    async def get_available_voices() -> list[dict]:
        voices = await edge_tts.list_voices()  # type: ignore[attr-defined]
        return voices  # type: ignore[return-value]

    @staticmethod
    def get_korean_voices() -> dict[str, dict]:
        return KOREAN_VOICES.copy()

    @staticmethod
    def get_english_voices() -> dict[str, dict]:
        return ENGLISH_VOICES.copy()

    def get_voice_for_language(
        self,
        language: str,
        gender: VoiceGender = "Female",
    ) -> str:
        lang_lower = language.lower()

        if lang_lower in ("ko", "korean", "ko-kr"):
            voices = KOREAN_VOICES
            default = self.DEFAULT_VOICE_KO
        else:
            voices = ENGLISH_VOICES
            default = self.DEFAULT_VOICE_EN

        for voice_id, info in voices.items():
            if info["gender"] == gender:
                return voice_id

        return default

    def adjust_rate_for_emotion(self, emotion: str) -> str:
        emotion_rates = {
            "excited": "+15%",
            "happy": "+10%",
            "neutral": "+0%",
            "sad": "-10%",
            "serious": "-5%",
            "angry": "+5%",
            "fearful": "+10%",
            "suspenseful": "-15%",
        }
        return emotion_rates.get(emotion.lower(), "+0%")

    def adjust_pitch_for_emotion(self, emotion: str) -> str:
        emotion_pitches = {
            "excited": "+50Hz",
            "happy": "+30Hz",
            "neutral": "+0Hz",
            "sad": "-30Hz",
            "serious": "-20Hz",
            "angry": "+20Hz",
            "fearful": "+40Hz",
            "suspenseful": "-10Hz",
        }
        return emotion_pitches.get(emotion.lower(), "+0Hz")
