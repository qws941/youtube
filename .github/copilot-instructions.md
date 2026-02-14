# Copilot Instructions — YouTube Automation System

AI-powered faceless YouTube channel automation. Generates and uploads videos for 3 channels (Horror, Facts, Finance) using LLM scripting, TTS, AI visuals, FFmpeg composition, and YouTube API uploads.

## Architecture

All services implement ABCs from `src/core/interfaces.py` (8 interfaces: ScriptGenerator, TTSEngine, ImageGenerator, VideoGenerator, VideoComposer, ThumbnailGenerator, YouTubeUploader, ContentPipeline). Constructor injection for DI; factory via `create_pipeline()`.

### Pipeline Flow

```
Topic (LLM) → Script (LLM) → Validation (word count, forbidden topics)
→ Audio (TTS) → Visuals (Image AI → Video clips) → Composition (FFmpeg)
→ Thumbnail (AI + Pillow) → YouTube Upload (OAuth2, resumable)
```

### Key Directories

| Path | Purpose |
|------|---------|
| `src/core/` | ABCs, models, exceptions, orchestrator |
| `src/services/` | llm, tts, visual, video, thumbnail, youtube |
| `src/channels/` | horror, facts, finance (each has pipeline.py + prompts.py) |
| `config/settings.py` | Pydantic settings (reads .env) |
| `data/templates/` | Prompt templates |
| `deploy/ffmpeg-worker/` | Remote FFmpeg FastAPI worker |

## Coding Conventions

### Async-First

ALL I/O operations MUST use `async/await`. Never use synchronous I/O in the pipeline — it blocks the event loop.

```python
# CORRECT
async def generate_script(self, topic: str) -> Script:
    response = await self.client.messages.create(...)

# WRONG — blocks event loop
def generate_script(self, topic: str) -> Script:
    response = self.client.messages.create(...)
```

### Logging

Always use structlog:

```python
import structlog
logger = structlog.get_logger(__name__)
```

### Error Handling

Use the custom exception hierarchy from `src/core/exceptions.py`:

- `YTAutoError` (base)
  - `LLMError` → `RateLimitError`, `ContentFilterError`
  - `TTSError` → `TTSQuotaExceededError`
  - `ImageGenerationError`, `VideoGenerationError`
  - `VideoCompositionError` → `FFmpegError`
  - `YouTubeAPIError` → `YouTubeQuotaExceededError`, `YouTubeAuthError`, `YouTubeUploadError`
  - `ScriptValidationError(issues: list[str])`
  - `PipelineError(stage, original_error)`
  - `ConfigurationError`, `AssetNotFoundError`

Never use bare `except Exception`. Catch specific exceptions from the hierarchy.

### Type Hints

mypy enforced (strict=false, ignore_missing_imports=true). All function signatures must have type annotations. Use `from __future__ import annotations` for forward references.

### Service Fallback Chain

Each service has a primary and fallback provider:

| Service | Primary | Fallback |
|---------|---------|----------|
| LLM | Claude (Anthropic) | GPT-4o (OpenAI) |
| TTS | ElevenLabs | Edge TTS |
| Images | Replicate (SDXL) | DALL-E 3 |
| Video | Runway | Ken Burns effect |

### Pydantic Models

Data models live in `src/core/models.py`. Use Pydantic BaseModel or dataclasses — not raw dicts.

## Channel Specifications

| Channel | Schedule | Duration | Word Count | Voice Style |
|---------|----------|----------|------------|-------------|
| Horror | Mon/Wed/Fri 6PM | 8-12 min | 1200-2000 | Dark, slow |
| Facts | Tue/Thu/Sat 6PM | 5-8 min | 800-1500 | Upbeat |
| Finance | Daily 9AM | 5-10 min | 1000-1800 | Professional |

## Hard Rules (NEVER Violate)

- **NEVER** hardcode API keys — use `.env` + Pydantic settings
- **NEVER** use sync I/O in pipeline code
- **NEVER** skip script validation (word count + forbidden topics check)
- **NEVER** upload a video without a thumbnail (kills CTR)
- **NEVER** exceed 100 characters in YouTube title (API rejects it)
- **NEVER** suppress type errors with `as any`, `@ts-ignore`, or `type: ignore`
- **Finance channel**: ALWAYS include a financial disclaimer

## Testing

pytest with asyncio_mode="auto". Tests in `tests/`. Coverage target via codecov.

```bash
pytest tests/ -v --cov=src --cov-report=xml
ruff check src/ tests/
mypy src/
```

## Configuration

All secrets via environment variables (see `.env.example`):
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `REPLICATE_API_TOKEN`, `RUNWAY_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`

Pydantic settings class in `config/settings.py` reads these automatically.

## Code Style

- Formatter/linter: `ruff` (line-length=100, target=py311)
- Rules: E, F, I, N, W, UP, B, C4, SIM
- Import sorting: isort-compatible via ruff
