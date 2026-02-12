# PROJECT KNOWLEDGE BASE

**Project:** YouTube Automation System  
**Type:** AI-powered Faceless YouTube Channel Automation

## OVERVIEW

Generates and uploads faceless YouTube videos for 3 channels (Horror, Facts, Finance) using AI for script generation, TTS, visual generation, and automated publishing.

## STRUCTURE

```
youtube/
├── src/
│   ├── cli.py          # Typer CLI entry (ytauto = src.cli:main, 438 lines)
│   ├── core/           # ABCs, models, exceptions, orchestrator
│   ├── services/       # 6 service modules (llm, tts, visual, video, thumbnail, youtube)
│   ├── channels/       # 3 channel pipelines (horror, facts, finance)
│   └── utils/          # (empty)
├── config/             # settings.py (Pydantic), client_secrets.json
├── data/
│   ├── templates/      # Prompt templates
│   ├── assets/         # Fonts, background music
│   └── output/         # Generated videos (gitignored)
├── deploy/ffmpeg-worker/  # Remote FFmpeg FastAPI worker (Proxmox CT 201)
├── n8n/                # Supabase schema + channel workflow JSONs
├── tests/              # pytest-asyncio tests
├── .github/workflows/  # CI: ruff, mypy, pytest + codecov
├── Dockerfile          # Multi-stage build
├── docker-compose.yml  # Profiles: scheduler, generate, auth
└── pyproject.toml      # hatchling, ruff (line-length=100), mypy, pytest
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
| FFmpeg worker | `deploy/ffmpeg-worker/` |
| CI/CD pipeline | `.github/workflows/ci.yml` |
| Docker config | `Dockerfile`, `docker-compose.yml` |

## PIPELINE FLOW

```
Topic (LLM) → Script (LLM) → Validation (word count, forbidden topics)
→ Audio (TTS) → Visuals (Image AI → Video clips) → Composition (FFmpeg)
→ Thumbnail (AI + Pillow) → YouTube Upload (OAuth2, resumable)
```

## CHANNEL SPECIFICATIONS

| Channel | Schedule | Duration | Word Count | Voice |
|---------|----------|----------|------------|-------|
| Horror | Mon/Wed/Fri 6PM | 8-12 min | 1200-2000 | Dark, slow |
| Facts | Tue/Thu/Sat 6PM | 5-8 min | 800-1500 | Upbeat |
| Finance | Daily 9AM | 5-10 min | 1000-1800 | Professional |

## CONVENTIONS

- **Interfaces**: All services implement ABCs from `src/core/interfaces.py` (8 ABCs)
- **Async**: All I/O uses `async/await` — NEVER sync I/O in pipeline
- **Logging**: `structlog.get_logger(__name__)`
- **Exceptions**: Custom hierarchy from `src/core/exceptions.py`
- **Type hints**: mypy enforced (`strict=false`, `ignore_missing_imports=true`)
- **Models**: Pydantic/dataclass in `src/core/models.py`
- **Fallbacks**: Claude→GPT-4o, ElevenLabs→Edge TTS, Replicate→DALL-E, Runway→Ken Burns
- **DI**: Constructor injection, factory `create_pipeline()`

## ANTI-PATTERNS

- **NEVER** hardcode API keys (use `.env` + Pydantic settings)
- **NEVER** use sync I/O in pipeline (blocks event loop)
- **NEVER** skip script validation (word count, forbidden topics)
- **NEVER** upload without thumbnail (affects CTR)
- **NEVER** exceed 100 char title (YouTube rejects)
- **Finance**: ALWAYS add disclaimer text

## TESTING & CLI

```bash
# Run pipeline
ytauto run --channel {horror|facts|finance|all} [--count N] [--dry-run]
ytauto schedule start|stop|status
ytauto config show|youtube-auth

# Quality checks
ruff check . && ruff format --check .
mypy src/
pytest --cov=src

# Docker
docker compose --profile generate run --rm generate --channel horror --dry-run
docker compose --profile scheduler up -d
```

## ENVIRONMENT

Required in `.env`:
- `ANTHROPIC_API_KEY` — Claude (primary LLM)
- `OPENAI_API_KEY` — GPT-4o fallback + DALL-E 3
- `ELEVENLABS_API_KEY` — TTS (optional, falls back to Edge TTS)
- `REPLICATE_API_TOKEN` — SDXL images
- `RUNWAY_API_KEY` — Video gen (optional, falls back to Ken Burns)
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` — OAuth2

## INFRASTRUCTURE

- **Docker**: Multi-stage build, 3 profiles (scheduler, generate, auth)
- **FFmpeg Worker**: FastAPI on Proxmox CT 201 (`192.168.50.201:8000`)
- **Storage**: MinIO at `192.168.50.109` for video artifacts
- **n8n**: Supabase + workflow automation for channel scheduling
- **CI**: GitHub Actions → ruff, mypy (continue-on-error), pytest + ffmpeg + codecov
