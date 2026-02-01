"""All service modules."""
# LLM
from src.services.llm import (
    CHANNEL_PROMPTS,
    AnthropicClient,
    LLMClient,
    OpenAIClient,
    ScriptGeneratorImpl,
    get_llm_client,
    get_script_generator,
)

# Thumbnail
from src.services.thumbnail import (
    CHANNEL_STYLES,
    TextPosition,
    TextStyle,
    ThumbnailGenerator,
    ThumbnailStyle,
    get_style_by_name,
    get_styles_for_channel,
)

# TTS
from src.services.tts import (
    EdgeTTSClient,
    ElevenLabsClient,
    TTSEngineImpl,
)

# Video
from src.services.video import (
    MusicMixer,
    SubtitleEntry,
    SubtitleGenerator,
    SubtitleStyle,
    VideoComposer,
)

# Visual
from src.services.visual import (
    CHANNEL_MOTION_PRESETS,
    CHANNEL_STYLE_PRESETS,
    ImageGenerator,
    VideoGenerator,
)

# YouTube
from src.services.youtube import (
    SEOOptimizer,
    YouTubeAuth,
    YouTubeUploader,
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
