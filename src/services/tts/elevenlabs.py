from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import get_settings
from src.core.exceptions import TTSError, TTSQuotaExceededError
from src.core.models import AudioSegment


class ElevenLabsClient:
    BASE_URL = "https://api.elevenlabs.io/v1"
    MODEL_ID = "eleven_multilingual_v2"

    def __init__(
        self,
        api_key: str | None = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ):
        settings = get_settings()
        self._api_key = api_key or settings.tts.api_key.get_secret_value()
        self._stability = stability
        self._similarity_boost = similarity_boost
        self._style = style
        self._use_speaker_boost = use_speaker_boost
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={"xi-api-key": self._api_key},
            timeout=120.0,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Path | str,
        stability: float | None = None,
        similarity_boost: float | None = None,
    ) -> AudioSegment:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "text": text,
            "model_id": self.MODEL_ID,
            "voice_settings": {
                "stability": stability or self._stability,
                "similarity_boost": similarity_boost or self._similarity_boost,
                "style": self._style,
                "use_speaker_boost": self._use_speaker_boost,
            },
            "output_format": "mp3_44100_128",
        }

        try:
            with self._client.stream(
                "POST",
                f"/text-to-speech/{voice_id}/stream",
                json=payload,
            ) as response:
                if response.status_code == 401:
                    raise TTSError("Invalid ElevenLabs API key")
                if response.status_code == 429:
                    raise TTSQuotaExceededError("ElevenLabs quota exceeded")
                if response.status_code != 200:
                    raise TTSError(f"ElevenLabs API error: {response.status_code}")

                with open(output_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise TTSQuotaExceededError("ElevenLabs quota exceeded") from e
            raise TTSError(f"ElevenLabs HTTP error: {e}") from e
        except httpx.RequestError as e:
            raise TTSError(f"ElevenLabs request failed: {e}") from e

        duration = self._get_audio_duration(output_path)

        return AudioSegment(
            path=output_path,
            duration=duration,
            text=text,
            start_time=0.0,
            voice_id=voice_id,
        )

    def _get_audio_duration(self, path: Path) -> float:
        try:
            from mutagen.mp3 import MP3

            audio = MP3(path)
            if audio.info is None:
                return 0.0
            return audio.info.length  # type: ignore[return-value]
        except Exception:
            return 0.0

    def get_voices(self) -> list[dict[str, Any]]:
        try:
            response = self._client.get("/voices")
            response.raise_for_status()
            return response.json().get("voices", [])
        except httpx.HTTPError as e:
            raise TTSError(f"Failed to fetch voices: {e}") from e

    def get_user_subscription(self) -> dict[str, Any]:
        try:
            response = self._client.get("/user/subscription")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise TTSError(f"Failed to fetch subscription: {e}") from e
