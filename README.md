# YouTube Automation System

AI-powered Faceless YouTube channel automation for 3 channels: Horror, Facts, and Finance.

## Features

- **Multi-channel support**: Horror, Facts, Finance with channel-specific pipelines
- **AI Script Generation**: Claude/GPT-4o for high-quality, engaging scripts
- **Text-to-Speech**: ElevenLabs (primary) + Edge TTS (fallback)
- **Visual Generation**: Replicate SDXL / DALL-E 3 for images, Runway Gen-3 / Ken Burns for video
- **Video Composition**: FFmpeg-based with subtitles and background music
- **Thumbnail Generation**: AI images + Pillow overlays with 9 style presets
- **YouTube Integration**: OAuth2 auth, resumable uploads, SEO optimization
- **Scheduling**: Cron-based scheduler for automated publishing

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd money

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Fill in your API keys in `.env`:
```env
# LLM
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# TTS
ELEVENLABS_API_KEY=...

# Visual
REPLICATE_API_TOKEN=...
RUNWAY_API_KEY=...

# YouTube
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
```

3. Set up YouTube OAuth2:
```bash
ytauto config youtube-auth
```

## Usage

### Generate a Single Video

```bash
# Horror channel
ytauto run --channel horror

# Facts channel
ytauto run --channel facts

# Finance channel
ytauto run --channel finance

# All channels (1 video each)
ytauto run --channel all
```

### Generate Multiple Videos

```bash
# 3 horror videos
ytauto run --channel horror --count 3
```

### Scheduler

```bash
# Start scheduler (daemon)
ytauto schedule start

# Stop scheduler
ytauto schedule stop

# Check status
ytauto status
```

### Configuration

```bash
# Show current config
ytauto config show

# Show version
ytauto version
```

## Project Structure

```
money/
├── config/
│   ├── settings.py          # Pydantic settings
│   └── __init__.py
├── src/
│   ├── core/
│   │   ├── models.py         # Data models (Script, VideoProject, etc.)
│   │   ├── interfaces.py     # Abstract base classes
│   │   ├── exceptions.py     # Custom exceptions
│   │   ├── orchestrator.py   # Pipeline orchestrator
│   │   └── __init__.py
│   ├── services/
│   │   ├── llm/              # Anthropic + OpenAI clients
│   │   ├── tts/              # ElevenLabs + Edge TTS
│   │   ├── visual/           # Image + Video generation
│   │   ├── video/            # FFmpeg composition
│   │   ├── thumbnail/        # Thumbnail generation
│   │   └── youtube/          # YouTube API integration
│   ├── channels/
│   │   ├── horror/           # Horror channel pipeline
│   │   ├── facts/            # Facts channel pipeline
│   │   └── finance/          # Finance channel pipeline
│   ├── cli.py                # Typer CLI
│   └── __init__.py
├── data/
│   ├── templates/            # Prompt templates
│   ├── assets/               # Music, fonts, etc.
│   └── output/               # Generated videos
├── pyproject.toml
├── .env.example
└── README.md
```

## Channel Specifications

| Channel | Schedule | Target Duration | RPM | Style |
|---------|----------|-----------------|-----|-------|
| Horror | Mon/Wed/Fri 6PM | 8-12 min | $3-8 | Dark, mysterious |
| Facts | Tue/Thu/Sat 6PM | 5-8 min | $2-5 | Bright, educational |
| Finance | Daily 9AM | 5-10 min | $10-30 | Professional |

## Pipeline Flow

```
1. Topic Generation (LLM)
       ↓
2. Script Writing (LLM)
       ↓
3. Script Validation (Rules)
       ↓
4. Audio Generation (TTS)
       ↓
5. Visual Generation (Image AI → Video)
       ↓
6. Video Composition (FFmpeg)
       ↓
7. Thumbnail Generation (AI + Pillow)
       ↓
8. YouTube Upload (API)
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `OPENAI_API_KEY` | Yes | OpenAI API key (GPT-4o, DALL-E) |
| `ELEVENLABS_API_KEY` | No | ElevenLabs TTS (fallback: Edge TTS) |
| `REPLICATE_API_TOKEN` | No | Replicate SDXL (fallback: DALL-E) |
| `RUNWAY_API_KEY` | No | Runway Gen-3 (fallback: Ken Burns) |
| `YOUTUBE_CLIENT_ID` | Yes | YouTube OAuth2 client ID |
| `YOUTUBE_CLIENT_SECRET` | Yes | YouTube OAuth2 client secret |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check .

# Run type checking
mypy src/
```

## License

MIT
