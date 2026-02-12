# CORE MODULE

**Purpose:** Architecture definitions - interfaces, models, exceptions, orchestration

## KEY FILES

| File | Purpose |
|------|---------|
| `interfaces.py` | 8 ABC classes defining service contracts |
| `models.py` | Data models (Script, VideoProject, ChannelConfig) |
| `exceptions.py` | Custom exception hierarchy |
| `orchestrator.py` | Job scheduling, queue management, worker pool |

## INTERFACES (interfaces.py)

All service implementations MUST extend these ABCs:

| Interface | Methods | Implementors |
|-----------|---------|--------------|
| `ScriptGenerator` | `generate(topic, channel) → Script` | `llm/script_generator.py` |
| `TTSEngine` | `synthesize(text, output_path, voice_id)` | `tts/engine.py` |
| `ImageGenerator` | `generate(prompt, output_path)` | `visual/image_generator.py` |
| `VideoGenerator` | `generate_from_image(image, motion, duration)` | `visual/video_generator.py` |
| `VideoComposer` | `compose(project, output_path)` | `video/composer.py` |
| `ThumbnailGenerator` | `generate(title, channel, output_path)` | `thumbnail/generator.py` |
| `YouTubeUploader` | `upload(video, title, desc, tags, thumbnail)` | `youtube/uploader.py` |
| `ContentPipeline` | `run(channel) → VideoProject` | `channels/*/pipeline.py` |

## MODELS (models.py)

```python
# Key models
Script(title, hook, body, cta, channel)  # word_count property
VideoProject(id, channel, script, output_path, status)  # mark_completed/failed
ChannelType  # Enum: HORROR, FACTS, FINANCE
AudioSegment(content, voice_settings, duration)
VisualAsset(path, type, duration, prompt)
ChannelConfig(name, schedule, duration_range, voice_id, ...)
```

## EXCEPTIONS (exceptions.py)

```
YTAutoError (aliased as YouTubeAutomationError)
├── LLMError
│   ├── LLMRateLimitError
│   └── LLMContentFilterError
├── TTSError
│   └── TTSQuotaExceededError
├── ImageGenerationError
├── VideoGenerationError
├── VideoCompositionError
│   └── FFmpegError
├── MusicGenerationError
├── YouTubeAPIError
│   ├── YouTubeQuotaExceededError
│   ├── YouTubeAuthError
│   └── YouTubeUploadError
├── ThumbnailError
├── ScriptValidationError          # has .issues: list[str]
└── PipelineError                  # has .stage, .original_error
```

## ORCHESTRATOR (orchestrator.py)

- **Job Queue**: Async queue with configurable concurrency
- **Workers**: Worker pool pattern (`max_concurrent=2`)
- **Retry**: Exponential backoff (`max_retries=3`, `retry_delay * retries`)
- **Scheduling**: `schedule` library, per-channel times
- **Signals**: Graceful shutdown (SIGTERM, SIGINT)

```python
# Singleton access
orchestrator = get_orchestrator(max_concurrent=2, dry_run=False)
await orchestrator.start()  # Starts workers + scheduler
await orchestrator.enqueue("horror")  # Queue a job
await orchestrator.run_once("facts")  # Immediate execution
orchestrator.status()  # {"state": "running", "queue_size": 0, ...}
```
