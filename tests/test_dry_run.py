"""Unit tests for YouTube Automation pipelines - initialization and structure."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from src.channels.facts import FactsPipeline
from src.channels.finance import FinancePipeline
from src.channels.horror import HorrorPipeline
from src.core.interfaces import ContentPipeline
from src.core.models import ChannelType, Script


def create_mock_services() -> dict[str, Any]:
    """Create mock implementations of all pipeline services."""
    return {
        "script_generator": MagicMock(),
        "tts_engine": MagicMock(),
        "image_generator": MagicMock(),
        "video_generator": MagicMock(),
        "video_composer": MagicMock(),
        "thumbnail_generator": MagicMock(),
        "youtube_uploader": MagicMock(),
    }


def test_horror_pipeline_init():
    """Test HorrorPipeline initialization."""
    print("\n🎬 Testing Horror Pipeline...")

    services = create_mock_services()
    output_base = Path("data/output")

    pipeline = HorrorPipeline(
        script_generator=services["script_generator"],
        tts_engine=services["tts_engine"],
        image_generator=services["image_generator"],
        video_generator=services["video_generator"],
        video_composer=services["video_composer"],
        thumbnail_generator=services["thumbnail_generator"],
        youtube_uploader=services["youtube_uploader"],
        output_base=output_base,
    )

    # Verify initialization
    assert pipeline.channel_type == ChannelType.HORROR, "Wrong channel type"
    assert pipeline.output_base == output_base, "Wrong output base"
    assert isinstance(pipeline, ContentPipeline), "Does not implement ContentPipeline"
    assert hasattr(pipeline, "run"), "Missing run method"
    assert hasattr(pipeline, "run_batch"), "Missing run_batch method"

    print("  ✅ Horror Pipeline initialized correctly")


def test_facts_pipeline_init():
    """Test FactsPipeline initialization."""
    print("\n📚 Testing Facts Pipeline...")

    services = create_mock_services()
    output_base = Path("data/output")

    pipeline = FactsPipeline(
        script_generator=services["script_generator"],
        tts_engine=services["tts_engine"],
        image_generator=services["image_generator"],
        video_generator=services["video_generator"],
        video_composer=services["video_composer"],
        thumbnail_generator=services["thumbnail_generator"],
        youtube_uploader=services["youtube_uploader"],
        output_base=output_base,
    )

    # Verify initialization
    assert pipeline.channel_type == ChannelType.FACTS, "Wrong channel type"
    assert pipeline.output_base == output_base, "Wrong output base"
    assert isinstance(pipeline, ContentPipeline), "Does not implement ContentPipeline"
    assert hasattr(pipeline, "run"), "Missing run method"
    assert hasattr(pipeline, "run_batch"), "Missing run_batch method"

    print("  ✅ Facts Pipeline initialized correctly")


def test_finance_pipeline_init():
    """Test FinancePipeline initialization."""
    print("\n💰 Testing Finance Pipeline...")

    services = create_mock_services()
    output_base = Path("data/output")

    pipeline = FinancePipeline(
        script_generator=services["script_generator"],
        tts_engine=services["tts_engine"],
        image_generator=services["image_generator"],
        video_generator=services["video_generator"],
        video_composer=services["video_composer"],
        thumbnail_generator=services["thumbnail_generator"],
        youtube_uploader=services["youtube_uploader"],
        output_base=output_base,
    )

    # Verify initialization
    assert pipeline.channel_type == ChannelType.FINANCE, "Wrong channel type"
    assert pipeline.output_base == output_base, "Wrong output base"
    assert isinstance(pipeline, ContentPipeline), "Does not implement ContentPipeline"
    assert hasattr(pipeline, "run"), "Missing run method"
    assert hasattr(pipeline, "run_batch"), "Missing run_batch method"

    # Finance pipeline has disclaimer in script generation
    # (verified via prompt templates, not constant export)

    print("  ✅ Finance Pipeline initialized correctly")


def test_script_model():
    """Test Script model creation and word count."""
    print("\n📝 Testing Script Model...")

    script = Script(
        title="Test Title",
        hook="This is the hook",
        body="Word " * 1000,  # 1000 words
        cta="Subscribe!",
        channel=ChannelType.HORROR,
    )

    assert script.title == "Test Title", "Wrong title"
    assert script.word_count >= 1000, f"Word count too low: {script.word_count}"
    assert script.channel == ChannelType.HORROR, "Wrong channel"

    print("  ✅ Script model works correctly")


def test_channel_configs():
    """Test channel configurations are loaded."""
    print("\n⚙️ Testing Channel Configs...")

    from src.core.models import CHANNEL_CONFIGS

    assert ChannelType.HORROR in CHANNEL_CONFIGS, "Missing Horror config"
    assert ChannelType.FACTS in CHANNEL_CONFIGS, "Missing Facts config"
    assert ChannelType.FINANCE in CHANNEL_CONFIGS, "Missing Finance config"

    print("  ✅ All channel configs present")


def test_prompts_loaded():
    """Test that all prompt templates are loaded."""
    print("\n📋 Testing Prompt Templates...")

    from src.channels.facts.prompts import (
        TOPIC_GENERATION as FACTS_TOPIC,
    )
    from src.channels.finance.prompts import (
        TOPIC_GENERATION as FIN_TOPIC,
    )
    from src.channels.horror.prompts import FORBIDDEN_TOPICS, TOPIC_GENERATION

    assert "{count}" in TOPIC_GENERATION, "Horror topic template missing placeholder"
    assert "{count}" in FACTS_TOPIC, "Facts topic template missing placeholder"
    assert "{count}" in FIN_TOPIC, "Finance topic template missing placeholder"

    assert len(FORBIDDEN_TOPICS) > 0, "Horror forbidden topics empty"

    print("  ✅ All prompt templates loaded correctly")


def main():
    """Run all unit tests."""
    print("=" * 60)
    print("🧪 YouTube Automation System - Unit Tests")
    print("=" * 60)

    tests = [
        ("Horror Pipeline Init", test_horror_pipeline_init),
        ("Facts Pipeline Init", test_facts_pipeline_init),
        ("Finance Pipeline Init", test_finance_pipeline_init),
        ("Script Model", test_script_model),
        ("Channel Configs", test_channel_configs),
        ("Prompt Templates", test_prompts_loaded),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            test_fn()
            results[name] = True
        except Exception as e:
            print(f"  ❌ {name} FAILED: {e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
