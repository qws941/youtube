from __future__ import annotations


class YTAutoError(Exception):
    pass


YouTubeAutomationError = YTAutoError


class LLMError(YTAutoError):
    pass


class LLMRateLimitError(LLMError):
    pass


class LLMContentFilterError(LLMError):
    pass


class TTSError(YouTubeAutomationError):
    pass


class TTSQuotaExceededError(TTSError):
    pass


class ImageGenerationError(YouTubeAutomationError):
    pass


class VideoGenerationError(YouTubeAutomationError):
    pass


class VideoCompositionError(YouTubeAutomationError):
    pass


class FFmpegError(VideoCompositionError):
    pass


class MusicGenerationError(YouTubeAutomationError):
    pass


class YouTubeAPIError(YouTubeAutomationError):
    pass


class YouTubeQuotaExceededError(YouTubeAPIError):
    pass


class YouTubeAuthError(YouTubeAPIError):
    pass


class YouTubeUploadError(YouTubeAPIError):
    pass


class ThumbnailError(YouTubeAutomationError):
    pass


class ScriptValidationError(YouTubeAutomationError):
    def __init__(self, message: str, issues: list[str] | None = None):
        super().__init__(message)
        self.issues = issues or []


class PipelineError(YTAutoError):
    def __init__(
        self, message: str, stage: str | None = None, original_error: Exception | None = None
    ):
        super().__init__(message)
        self.stage = stage
        self.original_error = original_error


class ConfigurationError(YouTubeAutomationError):
    pass


class AssetNotFoundError(YouTubeAutomationError):
    pass


YouTubeError = YouTubeAPIError
UploadError = YouTubeUploadError
AuthenticationError = YouTubeAuthError
QuotaExceededError = YouTubeQuotaExceededError
RateLimitError = LLMRateLimitError
ValidationError = ScriptValidationError
