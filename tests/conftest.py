"""Pytest configuration and shared fixtures for YouTube Automation tests."""
from __future__ import annotations

import asyncio
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from src.core.orchestrator import Orchestrator


# ============================================
# Event Loop Fixtures
# ============================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================
# Singleton Reset Fixtures
# ============================================


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons before each test for isolation."""
    _reset_all_singletons()
    yield
    _reset_all_singletons()


def _reset_all_singletons():
    """Reset orchestrator and settings singletons."""
    from config.settings import reload_settings
    from src.core.orchestrator import reset_orchestrator

    reset_orchestrator()
    reload_settings()


# ============================================
# Environment Fixtures
# ============================================


@pytest.fixture
def dry_run_env(monkeypatch: pytest.MonkeyPatch):
    """Set DRY_RUN environment variable."""
    monkeypatch.setenv("DRY_RUN", "true")
    return True


@pytest.fixture
def mock_api_keys(monkeypatch: pytest.MonkeyPatch):
    """Set mock API keys for testing without real credentials."""
    mock_keys = {
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "OPENAI_API_KEY": "sk-test-key",
        "ELEVENLABS_API_KEY": "test-eleven-key",
        "REPLICATE_API_TOKEN": "test-replicate-token",
        "RUNWAY_API_KEY": "test-runway-key",
    }
    for key, value in mock_keys.items():
        monkeypatch.setenv(key, value)
    return mock_keys


@pytest.fixture
def empty_api_keys(monkeypatch: pytest.MonkeyPatch):
    """Remove all API keys (simulate dry-run scenario)."""
    keys_to_remove = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "ELEVENLABS_API_KEY",
        "REPLICATE_API_TOKEN",
        "RUNWAY_API_KEY",
        "YOUTUBE_CLIENT_ID",
        "YOUTUBE_CLIENT_SECRET",
    ]
    for key in keys_to_remove:
        monkeypatch.delenv(key, raising=False)
    return keys_to_remove


# ============================================
# Path Fixtures
# ============================================


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def tmp_assets_dir(tmp_path: Path) -> Path:
    """Create a temporary assets directory for tests."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "music").mkdir()
    (assets_dir / "fonts").mkdir()

    return assets_dir


# ============================================
# Mock Service Fixtures
# ============================================


@pytest.fixture
def mock_script_generator() -> MagicMock:
    """Create a mock ScriptGenerator."""
    from src.core.models import ChannelType, Script

    mock = MagicMock()
    mock.generate_topic = AsyncMock(return_value=["Test Topic 1", "Test Topic 2"])
    mock.generate_script = AsyncMock(
        return_value=Script(
            title="Test Video Title",
            hook="This is a compelling hook.",
            body="This is the main body content. " * 100,
            cta="Subscribe for more!",
            channel=ChannelType.HORROR,
        )
    )
    return mock


@pytest.fixture
def mock_tts_engine() -> MagicMock:
    """Create a mock TTSEngine."""
    mock = MagicMock()
    mock.synthesize = MagicMock(return_value=Path("/tmp/test_audio.mp3"))
    mock.get_duration = MagicMock(return_value=180.0)
    return mock


@pytest.fixture
def mock_image_generator() -> MagicMock:
    """Create a mock ImageGenerator."""
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=Path("/tmp/test_image.png"))
    return mock


@pytest.fixture
def mock_video_generator() -> MagicMock:
    """Create a mock VideoGenerator."""
    mock = MagicMock()
    mock.generate_from_image = AsyncMock(return_value=Path("/tmp/test_clip.mp4"))
    return mock


@pytest.fixture
def mock_video_composer() -> MagicMock:
    """Create a mock VideoComposer."""
    mock = MagicMock()
    mock.compose = AsyncMock(return_value=Path("/tmp/test_video.mp4"))
    return mock


@pytest.fixture
def mock_thumbnail_generator() -> MagicMock:
    """Create a mock ThumbnailGenerator."""
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=Path("/tmp/test_thumbnail.png"))
    return mock


@pytest.fixture
def mock_youtube_uploader() -> MagicMock:
    """Create a mock YouTubeUploader."""
    mock = MagicMock()
    mock.upload = AsyncMock(return_value="video_id_12345")
    mock.is_authenticated = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_services(
    mock_script_generator,
    mock_tts_engine,
    mock_image_generator,
    mock_video_generator,
    mock_video_composer,
    mock_thumbnail_generator,
    mock_youtube_uploader,
) -> dict[str, Any]:
    """Bundle all mock services together."""
    return {
        "script_generator": mock_script_generator,
        "tts_engine": mock_tts_engine,
        "image_generator": mock_image_generator,
        "video_generator": mock_video_generator,
        "video_composer": mock_video_composer,
        "thumbnail_generator": mock_thumbnail_generator,
        "youtube_uploader": mock_youtube_uploader,
    }


# ============================================
# Orchestrator Fixtures
# ============================================


@pytest.fixture
def orchestrator_dry_run() -> Orchestrator:
    """Create an orchestrator in dry-run mode for testing."""
    from src.core.orchestrator import Orchestrator

    return Orchestrator(
        max_concurrent=2,
        max_retries=3,
        retry_delay=0.1,
        dry_run=True,
    )


@pytest.fixture
def orchestrator_with_mock_pipeline(
    orchestrator_dry_run: Orchestrator,
) -> Orchestrator:
    """Create an orchestrator with a mock pipeline registered."""
    mock_pipeline = MagicMock()
    mock_pipeline.run = AsyncMock(return_value={"status": "completed"})

    orchestrator_dry_run.register_pipeline("horror", mock_pipeline)
    orchestrator_dry_run.register_pipeline("facts", mock_pipeline)
    orchestrator_dry_run.register_pipeline("finance", mock_pipeline)

    return orchestrator_dry_run


# ============================================
# Pipeline Fixtures
# ============================================


@pytest.fixture
def horror_pipeline(mock_services, tmp_output_dir):
    """Create a HorrorPipeline with mock services."""
    from src.channels.horror import HorrorPipeline

    return HorrorPipeline(
        script_generator=mock_services["script_generator"],
        tts_engine=mock_services["tts_engine"],
        image_generator=mock_services["image_generator"],
        video_generator=mock_services["video_generator"],
        video_composer=mock_services["video_composer"],
        thumbnail_generator=mock_services["thumbnail_generator"],
        youtube_uploader=mock_services["youtube_uploader"],
        output_base=tmp_output_dir,
    )


@pytest.fixture
def facts_pipeline(mock_services, tmp_output_dir):
    """Create a FactsPipeline with mock services."""
    from src.channels.facts import FactsPipeline

    return FactsPipeline(
        script_generator=mock_services["script_generator"],
        tts_engine=mock_services["tts_engine"],
        image_generator=mock_services["image_generator"],
        video_generator=mock_services["video_generator"],
        video_composer=mock_services["video_composer"],
        thumbnail_generator=mock_services["thumbnail_generator"],
        youtube_uploader=mock_services["youtube_uploader"],
        output_base=tmp_output_dir,
    )


@pytest.fixture
def finance_pipeline(mock_services, tmp_output_dir):
    """Create a FinancePipeline with mock services."""
    from src.channels.finance import FinancePipeline

    return FinancePipeline(
        script_generator=mock_services["script_generator"],
        tts_engine=mock_services["tts_engine"],
        image_generator=mock_services["image_generator"],
        video_generator=mock_services["video_generator"],
        video_composer=mock_services["video_composer"],
        thumbnail_generator=mock_services["thumbnail_generator"],
        youtube_uploader=mock_services["youtube_uploader"],
        output_base=tmp_output_dir,
    )


# ============================================
# Settings Fixtures
# ============================================


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Create test settings with temporary directories."""
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("ASSETS_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("TEMPLATES_DIR", str(tmp_path / "templates"))
    (tmp_path / "output").mkdir(exist_ok=True)
    (tmp_path / "assets").mkdir(exist_ok=True)
    (tmp_path / "templates").mkdir(exist_ok=True)

    from config.settings import reload_settings
    return reload_settings()


# ============================================
# Async Test Helpers
# ============================================


@pytest.fixture
def run_async():
    """Helper to run async functions in sync tests."""
    def _run_async(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return _run_async
