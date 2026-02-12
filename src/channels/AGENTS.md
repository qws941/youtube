# CHANNELS MODULE

**Purpose:** Channel-specific content pipelines — each with distinct topics, prompts, validation, and scheduling

## STRUCTURE

Each channel directory contains:
- `pipeline.py` — `ContentPipeline` ABC implementation with `create_pipeline()` factory
- `prompts.py` — `SYSTEM_PROMPT`, `TOPIC_PROMPT`, `SCRIPT_PROMPT` constants

## VALIDATION

`ScriptValidationError` raised if word count outside channel range (see root AGENTS.md for specs).

## FORBIDDEN TOPICS

- **Finance**: get-rich-quick, pump-and-dump, gambling, MLM, crypto guarantees
- **Horror**: excessive gore, suicide methods, child exploitation
- **Facts**: misinformation, conspiracy theories, pseudoscience

## CHANNEL RULES

- **Finance**: ALWAYS include disclaimer text in description
- **Horror**: Dark ambient background music, slow-paced narration
- **Facts**: Upbeat music, clear numbered sections
- Each channel defines its own prompt constants in `prompts.py`

## PIPELINE PATTERN

```python
class HorrorPipeline(ContentPipeline):
    @classmethod
    async def create_pipeline(cls, settings) -> "HorrorPipeline":
        # Factory: constructs all service dependencies via DI

    async def run(self, channel: str) -> VideoProject:
        # topic → script → validate → audio → visuals → compose → thumbnail → upload
```

## ADDING A NEW CHANNEL

1. Create `src/channels/{name}/` with `__init__.py`, `pipeline.py`, `prompts.py`
2. Implement `ContentPipeline` ABC with `create_pipeline()` factory
3. Define `SYSTEM_PROMPT`, `TOPIC_PROMPT`, `SCRIPT_PROMPT` in `prompts.py`
4. Add `ChannelType.{NAME}` enum value in `core/models.py`
5. Add elif branch in `orchestrator._lazy_load_pipeline()`
6. Register schedule in orchestrator
