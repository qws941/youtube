"""Tests for TTS Engine with fallback chain."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import TTSError, TTSQuotaExceededError
from src.core.models import AudioSegment, ChannelType


class TestTTSEngineInit:
    """Test TTS engine initialization."""

    def test_init_with_elevenlabs_preferred(self):
        """Test initialization with ElevenLabs as preferred provider."""
        with patch("src.services.tts.engine.get_settings") as mock_settings:
            mock_settings.return_value.tts.api_key.get_secret_value.return_value = "test-key"
            mock_settings.return_value.paths.output_dir = Path("/tmp/output")

            with patch("src.services.tts.engine.ElevenLabsClient") as mock_el:
                with patch("src.services.tts.engine.EdgeTTSClient") as mock_edge:
                    from src.services.tts.engine import TTSEngineImpl

                    engine = TTSEngineImpl(prefer_provider="elevenlabs")

                    assert engine._prefer_provider == "elevenlabs"
                    mock_el.assert_called_once()
                    mock_edge.assert_called_once()

    def test_init_with_edge_preferred(self):
        """Test initialization with Edge TTS as preferred provider."""
        with patch("src.services.tts.engine.get_settings") as mock_settings:
            mock_settings.return_value.tts.api_key.get_secret_value.return_value = ""
            mock_settings.return_value.paths.output_dir = Path("/tmp/output")

            with patch("src.services.tts.engine.EdgeTTSClient") as mock_edge:
                from src.services.tts.engine import TTSEngineImpl

                engine = TTSEngineImpl(prefer_provider="edge")

                assert engine._prefer_provider == "edge"
                mock_edge.assert_called_once()

    def test_init_with_custom_output_dir(self, tmp_path: Path):
        """Test initialization with custom output directory."""
        with patch("src.services.tts.engine.get_settings") as mock_settings:
            mock_settings.return_value.tts.api_key.get_secret_value.return_value = ""
            mock_settings.return_value.paths.output_dir = Path("/tmp/output")

            with patch("src.services.tts.engine.EdgeTTSClient"):
                from src.services.tts.engine import TTSEngineImpl

                engine = TTSEngineImpl(output_dir=tmp_path)

                assert engine._output_dir == tmp_path


class TestTTSSynthesize:
    """Test TTS synthesize method."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock TTS engine."""
        with patch("src.services.tts.engine.get_settings") as mock_settings:
            mock_settings.return_value.tts.api_key.get_secret_value.return_value = "test-key"
            mock_settings.return_value.paths.output_dir = Path("/tmp/output")

            with patch("src.services.tts.engine.ElevenLabsClient"):
                with patch("src.services.tts.engine.EdgeTTSClient"):
                    from src.services.tts.engine import TTSEngineImpl

                    engine = TTSEngineImpl(prefer_provider="elevenlabs")

                    engine._elevenlabs = MagicMock()
                    engine._edge = MagicMock()

                    yield engine

    def test_synthesize_uses_elevenlabs_when_preferred(self, mock_engine, tmp_path: Path):
        """Test that synthesize uses ElevenLabs when it's the preferred provider."""
        output_path = tmp_path / "test.mp3"
        expected_segment = AudioSegment(
            path=output_path,
            duration=5.0,
            text="Hello world",
            start_time=0.0,
            voice_id="test-voice",
        )
        mock_engine._elevenlabs.synthesize.return_value = expected_segment

        result = mock_engine._synthesize_sync(
            text="Hello world",
            output_path=output_path,
            channel_type=ChannelType.HORROR,
        )

        assert result == expected_segment
        mock_engine._elevenlabs.synthesize.assert_called_once()

    def test_synthesize_falls_back_to_edge_on_quota_exceeded(self, mock_engine, tmp_path: Path):
        """Test fallback to Edge TTS when ElevenLabs quota is exceeded."""
        output_path = tmp_path / "test.mp3"
        expected_segment = AudioSegment(
            path=output_path,
            duration=5.0,
            text="Hello world",
            start_time=0.0,
            voice_id="en-US-DavisNeural",
        )

        mock_engine._elevenlabs.synthesize.side_effect = TTSQuotaExceededError("Quota exceeded")
        mock_engine._edge.synthesize.return_value = expected_segment

        result = mock_engine._synthesize_sync(
            text="Hello world",
            output_path=output_path,
            channel_type=ChannelType.HORROR,
        )

        assert result == expected_segment
        mock_engine._edge.synthesize.assert_called_once()

    def test_synthesize_falls_back_to_edge_on_tts_error(self, mock_engine, tmp_path: Path):
        """Test fallback to Edge TTS on general TTS error."""
        output_path = tmp_path / "test.mp3"
        expected_segment = AudioSegment(
            path=output_path,
            duration=5.0,
            text="Hello world",
            start_time=0.0,
            voice_id="en-US-DavisNeural",
        )

        mock_engine._elevenlabs.synthesize.side_effect = TTSError("API error")
        mock_engine._edge.synthesize.return_value = expected_segment

        result = mock_engine._synthesize_sync(
            text="Hello world",
            output_path=output_path,
            channel_type=ChannelType.HORROR,
        )

        assert result == expected_segment

    def test_synthesize_raises_when_fallback_disabled(self, tmp_path: Path):
        """Test that error is raised when fallback is disabled."""
        with patch("src.services.tts.engine.get_settings") as mock_settings:
            mock_settings.return_value.tts.api_key.get_secret_value.return_value = "test-key"
            mock_settings.return_value.paths.output_dir = Path("/tmp/output")

            with patch("src.services.tts.engine.ElevenLabsClient"):
                with patch("src.services.tts.engine.EdgeTTSClient"):
                    from src.services.tts.engine import TTSEngineImpl

                    engine = TTSEngineImpl(prefer_provider="elevenlabs", auto_fallback=False)
                    engine._elevenlabs = MagicMock()
                    engine._elevenlabs.synthesize.side_effect = TTSQuotaExceededError(
                        "Quota exceeded"
                    )

                    with pytest.raises(TTSQuotaExceededError):
                        engine._synthesize_sync(
                            text="Hello world",
                            output_path=tmp_path / "test.mp3",
                        )

    def test_synthesize_raises_when_no_provider_available(self, tmp_path: Path):
        """Test that error is raised when no TTS provider is available."""
        with patch("src.services.tts.engine.get_settings") as mock_settings:
            mock_settings.return_value.tts.api_key.get_secret_value.return_value = ""
            mock_settings.return_value.paths.output_dir = Path("/tmp/output")

            with patch("src.services.tts.engine.EdgeTTSClient"):
                from src.services.tts.engine import TTSEngineImpl

                engine = TTSEngineImpl(prefer_provider="edge")
                engine._edge = None

                with pytest.raises(TTSError, match="No TTS provider available"):
                    engine._synthesize_sync(
                        text="Hello world",
                        output_path=tmp_path / "test.mp3",
                    )


class TestChannelVoiceMapping:
    """Test channel to voice mapping."""

    def test_horror_channel_uses_correct_voices(self):
        """Test Horror channel voice mappings."""
        from src.services.tts.engine import CHANNEL_VOICE_MAP, ChannelType

        horror_voices = CHANNEL_VOICE_MAP[ChannelType.HORROR]

        assert "elevenlabs" in horror_voices
        assert "edge" in horror_voices
        assert horror_voices["edge"] == "en-US-DavisNeural"

    def test_facts_channel_uses_correct_voices(self):
        """Test Facts channel voice mappings."""
        from src.services.tts.engine import CHANNEL_VOICE_MAP, ChannelType

        facts_voices = CHANNEL_VOICE_MAP[ChannelType.FACTS]

        assert "elevenlabs" in facts_voices
        assert "edge" in facts_voices
        assert facts_voices["edge"] == "en-US-AriaNeural"

    def test_finance_channel_uses_correct_voices(self):
        """Test Finance channel voice mappings."""
        from src.services.tts.engine import CHANNEL_VOICE_MAP, ChannelType

        finance_voices = CHANNEL_VOICE_MAP[ChannelType.FINANCE]

        assert "elevenlabs" in finance_voices
        assert "edge" in finance_voices
        assert finance_voices["edge"] == "en-US-GuyNeural"


class TestEmotionVoiceSettings:
    """Test emotion-based voice settings."""

    def test_all_emotions_have_settings(self):
        """Test that all expected emotions have voice settings."""
        from src.services.tts.engine import EMOTION_VOICE_SETTINGS

        expected_emotions = [
            "neutral",
            "excited",
            "sad",
            "angry",
            "fearful",
            "suspenseful",
            "serious",
            "happy",
        ]

        for emotion in expected_emotions:
            assert emotion in EMOTION_VOICE_SETTINGS
            settings = EMOTION_VOICE_SETTINGS[emotion]
            assert "stability" in settings
            assert "similarity_boost" in settings
            assert 0.0 <= settings["stability"] <= 1.0
            assert 0.0 <= settings["similarity_boost"] <= 1.0


class TestEmotionParsing:
    """Test emotion marker parsing."""

    @pytest.fixture
    def engine(self):
        """Create a minimal engine for testing parsing."""
        with patch("src.services.tts.engine.get_settings") as mock_settings:
            mock_settings.return_value.tts.api_key.get_secret_value.return_value = ""
            mock_settings.return_value.paths.output_dir = Path("/tmp/output")

            with patch("src.services.tts.engine.EdgeTTSClient"):
                from src.services.tts.engine import TTSEngineImpl

                yield TTSEngineImpl(prefer_provider="edge")

    def test_parse_no_emotion_markers(self, engine):
        """Test parsing text without emotion markers."""
        text = "This is plain text without markers."

        result = engine._parse_emotion_markers(text)

        assert len(result) == 1
        assert result[0] == ("neutral", text)

    def test_parse_single_emotion_marker(self, engine):
        """Test parsing text with single emotion marker."""
        text = "[excited]This is exciting news!"

        result = engine._parse_emotion_markers(text)

        assert len(result) == 1
        assert result[0][0] == "excited"
        assert result[0][1] == "This is exciting news!"

    def test_parse_multiple_emotion_markers(self, engine):
        """Test parsing text with multiple emotion markers."""
        text = "[happy]Hello there! [sad]But then something bad happened. [excited]And then it got better!"

        result = engine._parse_emotion_markers(text)

        assert len(result) == 3
        assert result[0][0] == "happy"
        assert result[1][0] == "sad"
        assert result[2][0] == "excited"

    def test_parse_emotion_markers_case_insensitive(self, engine):
        """Test that emotion markers are parsed case-insensitively."""
        text = "[EXCITED]This is EXCITING!"

        result = engine._parse_emotion_markers(text)

        assert result[0][0] == "excited"


class TestGetVoiceForChannel:
    """Test voice selection for channels."""

    @pytest.fixture
    def engine(self):
        """Create engine for testing."""
        with patch("src.services.tts.engine.get_settings") as mock_settings:
            mock_settings.return_value.tts.api_key.get_secret_value.return_value = ""
            mock_settings.return_value.paths.output_dir = Path("/tmp/output")

            with patch("src.services.tts.engine.EdgeTTSClient"):
                from src.services.tts.engine import TTSEngineImpl

                yield TTSEngineImpl(prefer_provider="edge")

    def test_get_voice_for_horror_channel(self, engine):
        """Test getting voice for Horror channel."""
        voice = engine._get_voice_for_channel(ChannelType.HORROR, "edge")
        assert voice == "en-US-DavisNeural"

    def test_get_voice_for_none_channel_defaults_to_facts(self, engine):
        """Test that None channel defaults to Facts channel voice."""
        voice = engine._get_voice_for_channel(None, "edge")
        assert voice == "en-US-AriaNeural"
