"""All service modules."""
# LLM
from src.services.llm import (
    LLMClient,
    AnthropicClient,
    OpenAIClient,
    get_llm_client,
    ScriptGeneratorImpl,
    get_script_generator,
    CHANNEL_PROMPTS,
)

# TTS
from src.services.tts import (
    ElevenLabsClient,
    EdgeTTSClient,
    TTSEngineImpl,
)

# Visual
from src.services.visual import (
    ImageGenerator,
    VideoGenerator,
    CHANNEL_STYLE_PRESETS,
    CHANNEL_MOTION_PRESETS,
)

# Video
from src.services.video import (
    VideoComposer,
    SubtitleGenerator,
    SubtitleStyle,
    SubtitleEntry,
    MusicMixer,
)

# Thumbnail
from src.services.thumbnail import (
    ThumbnailGenerator,
    ThumbnailStyle,
    TextStyle,
    TextPosition,
    CHANNEL_STYLES,
    get_styles_for_channel,
    get_style_by_name,
)

# YouTube
from src.services.youtube import (
    YouTubeAuth,
    YouTubeUploader,
    SEOOptimizer,
)

__all__ = [
    # LLM
    "LLMClient",
    "AnthropicClient",
    "OpenAIClient",
    "get_llm_client",
    "ScriptGeneratorImpl",
    "get_script_generator",
    "CHANNEL_PROMPTS",
    # TTS
    "ElevenLabsClient",
    "EdgeTTSClient",
    "TTSEngineImpl",
    # Visual
    "ImageGenerator",
    "VideoGenerator",
    "CHANNEL_STYLE_PRESETS",
    "CHANNEL_MOTION_PRESETS",
    # Video
    "VideoComposer",
    "SubtitleGenerator",
    "SubtitleStyle",
    "SubtitleEntry",
    "MusicMixer",
    # Thumbnail
    "ThumbnailGenerator",
    "ThumbnailStyle",
    "TextStyle",
    "TextPosition",
    "CHANNEL_STYLES",
    "get_styles_for_channel",
    "get_style_by_name",
    # YouTube
    "YouTubeAuth",
    "YouTubeUploader",
    "SEOOptimizer",
]
