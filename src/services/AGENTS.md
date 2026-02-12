# SERVICES MODULE

**Purpose:** External API integrations implementing core interfaces

## STRUCTURE

```
services/
├── llm/          # Script generation (Claude, GPT-4o)
├── tts/          # Text-to-Speech (ElevenLabs, Edge TTS)
├── visual/       # Image + Video generation (Replicate, DALL-E, Runway)
├── video/        # FFmpeg composition, subtitles, music
├── thumbnail/    # AI thumbnails + Pillow overlays
└── youtube/      # YouTube Data API v3
```

## SERVICE PATTERNS

All services follow these patterns:

1. **Interface Implementation**: Each extends ABC from `core/interfaces.py`
2. **Async I/O**: All external calls use `async/await`
3. **Fallback Chain**: Primary → Fallback (e.g., ElevenLabs → Edge TTS)
4. **Error Wrapping**: Catch provider errors, raise domain exceptions

## SERVICE DETAILS

### LLM (`llm/`)
- `client.py` — Anthropic + OpenAI client wrappers
- `script_generator.py` — `ScriptGenerator` ABC impl
- **Fallback**: Claude Sonnet → GPT-4o

### TTS (`tts/`)
- `engine.py` — `TTSEngine` interface + fallback logic
- `elevenlabs.py` — ElevenLabs provider
- `edge_tts.py` — Microsoft Edge TTS (free fallback)
- **Fallback**: ElevenLabs → Edge TTS (free, unlimited)

### Visual (`visual/`)
- `image_generator.py` — `ImageGenerator` (Replicate SDXL, DALL-E 3)
- `video_generator.py` — `VideoGenerator` (Runway Gen-3, Ken Burns)
- **Fallback**: Replicate → DALL-E 3, Runway → Ken Burns effect

### Video (`video/`)
- `composer.py` — `VideoComposer` (FFmpeg subprocess, NO moviepy)
- `subtitles.py` — SRT generation + styling
- `music.py` — Background music mixing

### Thumbnail (`thumbnail/`)
- `generator.py` — `ThumbnailGenerator` impl
- `styles.py` — 9 preset styles per channel
- **Process**: AI image → Pillow overlay (title, branding)

### YouTube (`youtube/`)
- `uploader.py` — `YouTubeUploader` (resumable uploads, auto token refresh)
- `auth.py` — OAuth2 flow, token refresh
- `seo.py` — Title/description/tag optimization
