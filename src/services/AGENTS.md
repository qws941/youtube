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

## LLM SERVICE (`llm/`)

| File | Purpose |
|------|---------|
| `client.py` | Anthropic + OpenAI client wrappers |
| `script_generator.py` | `ScriptGenerator` implementation |

```python
# Usage
generator = ScriptGenerator(client=AnthropicClient())
script = await generator.generate(topic="...", channel=ChannelType.HORROR)
```

**Fallback**: Claude Sonnet → GPT-4o

## TTS SERVICE (`tts/`)

| File | Purpose |
|------|---------|
| `engine.py` | `TTSEngine` interface, fallback logic |
| `elevenlabs.py` | ElevenLabs provider |
| `edge_tts.py` | Microsoft Edge TTS (free fallback) |

```python
# Usage
engine = TTSEngine(elevenlabs_key="...", fallback=True)
await engine.synthesize(text="...", output_path=Path("audio.mp3"), voice_id="...")
```

**Fallback**: ElevenLabs → Edge TTS (free, unlimited)

## VISUAL SERVICE (`visual/`)

| File | Purpose |
|------|---------|
| `image_generator.py` | `ImageGenerator` (Replicate SDXL, DALL-E 3) |
| `video_generator.py` | `VideoGenerator` (Runway Gen-3, Ken Burns) |

```python
# Image
await image_gen.generate(prompt="...", output_path=Path("scene.png"))

# Video from image
await video_gen.generate_from_image(
    image_path=Path("scene.png"),
    motion_prompt="slow zoom in",
    duration=5.0,
    output_path=Path("clip.mp4")
)
```

**Fallback**: Replicate → DALL-E 3, Runway → Ken Burns effect

## VIDEO SERVICE (`video/`)

| File | Purpose |
|------|---------|
| `composer.py` | `VideoComposer` (FFmpeg orchestration) |
| `subtitles.py` | SRT generation, styling |
| `music.py` | Background music mixing |

```python
# Usage
composer = VideoComposer(ffmpeg_path="ffmpeg")
await composer.compose(project=video_project, output_path=Path("final.mp4"))
```

**Key**: Uses FFmpeg subprocess, NO moviepy for main composition

## THUMBNAIL SERVICE (`thumbnail/`)

| File | Purpose |
|------|---------|
| `generator.py` | `ThumbnailGenerator` implementation |
| `styles.py` | 9 preset styles per channel |

```python
# Usage
await thumb_gen.generate(
    title="Video Title",
    channel=ChannelType.HORROR,
    output_path=Path("thumb.png")
)
```

**Process**: AI image → Pillow overlay (title, branding)

## YOUTUBE SERVICE (`youtube/`)

| File | Purpose |
|------|---------|
| `uploader.py` | `YouTubeUploader` (resumable uploads) |
| `auth.py` | OAuth2 flow, token refresh |
| `seo.py` | Title/description/tag optimization |

```python
# Usage
await uploader.upload(
    video_path=Path("final.mp4"),
    title="...",
    description="...",
    tags=["horror", "mystery"],
    thumbnail_path=Path("thumb.png"),
    scheduled_at="2024-01-01T18:00:00Z"
)
```

**Key**: Resumable upload for large files, auto token refresh

## ADDING A NEW SERVICE

1. Create directory: `src/services/{name}/`
2. Add ABC to `core/interfaces.py`
3. Implement interface in `{name}/{impl}.py`
4. Register in `__init__.py`
5. Wire into pipeline in `channels/*/pipeline.py`

## API KEYS (from settings)

| Service | Setting Path | Env Variable |
|---------|--------------|--------------|
| LLM | `settings.llm.anthropic_api_key` | `ANTHROPIC_API_KEY` |
| LLM | `settings.llm.openai_api_key` | `OPENAI_API_KEY` |
| TTS | `settings.tts.elevenlabs_api_key` | `ELEVENLABS_API_KEY` |
| Visual | `settings.visual.replicate_api_token` | `REPLICATE_API_TOKEN` |
| Visual | `settings.visual.runway_api_key` | `RUNWAY_API_KEY` |
| YouTube | `settings.youtube.client_id` | `YOUTUBE_CLIENT_ID` |
