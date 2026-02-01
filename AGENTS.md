# PROJECT KNOWLEDGE BASE

**Project:** YouTube Automation System  
**Type:** AI-powered Faceless YouTube Channel Automation

## OVERVIEW

Generates and uploads faceless YouTube videos for 3 channels (Horror, Facts, Finance) using AI for script generation, TTS, visual generation, and automated publishing.

## STRUCTURE

```
money/
├── src/
│   ├── core/           # ABC interfaces, models, exceptions, orchestrator
│   ├── services/       # External API integrations (6 modules)
│   │   ├── llm/        # Claude/GPT-4o script generation
│   │   ├── tts/        # ElevenLabs + Edge TTS
│   │   ├── visual/     # Replicate SDXL, DALL-E 3
│   │   ├── video/      # FFmpeg composition
│   │   ├── thumbnail/  # AI + Pillow thumbnails
│   │   └── youtube/    # YouTube Data API v3
│   ├── channels/       # Channel-specific pipelines
│   │   ├── horror/     # Horror channel (Mon/Wed/Fri)
│   │   ├── facts/      # Facts channel (Tue/Thu/Sat)
│   │   └── finance/    # Finance channel (Daily)
│   └── cli.py          # Typer CLI entry point
├── config/
│   └── settings.py     # Pydantic nested settings
├── data/
│   ├── templates/      # Prompt templates
│   ├── assets/         # Music, fonts
│   └── output/         # Generated videos
└── pyproject.toml
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Add new channel | `src/channels/{name}/pipeline.py` + `prompts.py` |
| Modify script generation | `src/services/llm/script_generator.py` |
| Change TTS provider | `src/services/tts/engine.py` |
| Adjust video composition | `src/services/video/composer.py` |
| Add thumbnail style | `src/services/thumbnail/styles.py` |
| Modify scheduling | `src/core/orchestrator.py` |
| Add CLI command | `src/cli.py` |
| Configure API keys | `.env` + `config/settings.py` |

## PIPELINE FLOW

```
Topic Generation (LLM)
       ↓
Script Writing (LLM)
       ↓
Script Validation (word count, forbidden topics)
       ↓
Audio Generation (TTS)
       ↓
Visual Generation (Image AI → Video clips)
       ↓
Video Composition (FFmpeg)
       ↓
Thumbnail Generation (AI + Pillow)
       ↓
YouTube Upload (OAuth2, resumable)
```

## CHANNEL SPECIFICATIONS

| Channel | Schedule | Duration | RPM | Voice Style |
|---------|----------|----------|-----|-------------|
| Horror | Mon/Wed/Fri 6PM | 8-12 min | $3-8 | Dark, slow |
| Facts | Tue/Thu/Sat 6PM | 5-8 min | $2-5 | Upbeat, clear |
| Finance | Daily 9AM | 5-10 min | $10-30 | Professional |

## CONVENTIONS

- **Interfaces**: All services implement ABCs from `src/core/interfaces.py`
- **Async**: All I/O operations are async (`async/await`)
- **Logging**: structlog with `logger = structlog.get_logger(__name__)`
- **Exceptions**: Custom hierarchy from `src/core/exceptions.py`
- **Type hints**: Strict (mypy enforced)
- **Models**: Pydantic/dataclass in `src/core/models.py`

## ANTI-PATTERNS

- **NEVER** hardcode API keys (use `.env` + settings)
- **NEVER** use sync I/O in pipeline (blocks event loop)
- **NEVER** skip script validation (word count, forbidden topics)
- **NEVER** upload without thumbnail (affects CTR)
- **NEVER** exceed 100 char title limit (YouTube rejects)

## TESTING

```bash
# Dry run (no API calls, no upload)
ytauto run --channel horror --dry-run

# Run linting
ruff check .

# Run type checking
mypy src/
```

## ENVIRONMENT

Required API keys in `.env`:
- `ANTHROPIC_API_KEY` - Claude (primary LLM)
- `OPENAI_API_KEY` - GPT-4o fallback, DALL-E
- `ELEVENLABS_API_KEY` - TTS (optional, falls back to Edge TTS)
- `REPLICATE_API_TOKEN` - SDXL images
- `RUNWAY_API_KEY` - Video generation (optional, falls back to Ken Burns)
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` - OAuth2

## CLI COMMANDS

```bash
ytauto run --channel {horror|facts|finance|all} [--count N] [--dry-run]
ytauto schedule start|stop|status
ytauto config show|youtube-auth
ytauto version
```
