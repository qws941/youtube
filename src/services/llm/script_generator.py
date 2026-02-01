from typing import Any
import re

from src.core.interfaces import ScriptGenerator as ScriptGeneratorABC
from src.core.models import Script, ChannelType
from src.core.exceptions import LLMError
from src.services.llm.client import LLMClient, get_llm_client


CHANNEL_PROMPTS = {
    ChannelType.HORROR: {
        "topic_system": """You are a viral horror/mystery content strategist. 
Generate unique, clickable topic ideas that evoke fear, curiosity, and the unknown.
Focus on: unsolved mysteries, creepy true stories, urban legends, paranormal events.""",
        "topic_prompt": """Generate a compelling horror/mystery video topic.
Requirements:
- Must be attention-grabbing and curiosity-inducing
- Should hint at something disturbing or unexplained
- Avoid overused topics
- Target audience: young adults who love scary content

Return ONLY the topic title as a single line, no JSON, no explanation.""",
        "script_system": """You are an expert horror storytelling scriptwriter for YouTube.
Write scripts that build tension, create suspense, and deliver satisfying reveals.
Use pacing techniques: slow build, sudden shifts, ominous pauses.""",
        "emotion_markers": ["suspense", "dread", "revelation", "twist", "unease"],
    },
    ChannelType.FACTS: {
        "topic_system": """You are a viral educational content strategist.
Generate fascinating fact-based topics that make viewers say "I never knew that!"
Focus on: surprising science, historical oddities, psychology, nature's wonders.""",
        "topic_prompt": """Generate an engaging educational/facts video topic.
Requirements:
- Must contain genuinely surprising information
- Should challenge common assumptions
- Appeal to curious minds of all ages
- High shareability factor

Return ONLY the topic title as a single line, no JSON, no explanation.""",
        "script_system": """You are an expert educational content scriptwriter for YouTube.
Write scripts that deliver "wow" moments, explain complex ideas simply, and maintain engagement.
Use the curiosity gap technique and surprising reveals.""",
        "emotion_markers": ["surprise", "amazement", "curiosity", "realization", "fascination"],
    },
    ChannelType.FINANCE: {
        "topic_system": """You are a viral personal finance content strategist.
Generate actionable money topics that create urgency and promise transformation.
Focus on: money mistakes, wealth building, market insights, financial psychology.""",
        "topic_prompt": """Generate a compelling finance video topic.
Requirements:
- Must have clear actionable value
- Should create sense of urgency or FOMO
- Appeal to aspiring wealth builders
- Avoid generic "how to budget" content

Return ONLY the topic title as a single line, no JSON, no explanation.""",
        "script_system": """You are an expert finance content scriptwriter for YouTube.
Write scripts that deliver valuable insights with urgency, using real examples and clear actionables.
Create FOMO around missed opportunities and promise of transformation.""",
        "emotion_markers": ["urgency", "opportunity", "warning", "revelation", "motivation"],
    },
}

SCRIPT_PROMPT_TEMPLATE = """Write a YouTube script for the following topic:
Topic: {topic}
Channel Type: {channel_type}
Target Length: 8-12 minutes when spoken

STRUCTURE (REQUIRED):
1. HOOK (first 5 seconds): Pattern interrupt, shocking statement, or provocative question that stops scrolling
2. BODY: Main content with 3-5 key points, each building on the last. Include {emotion_markers}.
3. CTA: Subtle call-to-action for subscription, integrated naturally into closing

Return JSON:
{{
    "title": "SEO-optimized title (under 60 chars)",
    "hook": "The first 5 seconds hook script",
    "body": "Full body script with clear section breaks marked as [SECTION]",
    "cta": "Subscription call-to-action",
    "emotion_markers": [
        {{"timestamp": "MM:SS", "type": "marker_type", "text": "line that triggers emotion"}}
    ],
    "keywords": ["seo", "keywords"]
}}"""


class ScriptGeneratorImpl(ScriptGeneratorABC):
    def __init__(self, llm_client: LLMClient | None = None, provider: str = "anthropic"):
        self._client = llm_client or get_llm_client(provider)

    async def generate_topic(self, channel: ChannelType) -> str:
        prompts = CHANNEL_PROMPTS.get(channel)
        if not prompts:
            raise LLMError(f"No prompts configured for channel: {channel}")
        
        result = await self._client.generate(
            prompt=prompts["topic_prompt"],
            system=prompts["topic_system"],
            temperature=0.9,
        )
        return result.strip()

    async def generate_script(self, topic: str, channel: ChannelType) -> Script:
        prompts = CHANNEL_PROMPTS.get(channel)
        if not prompts:
            raise LLMError(f"No prompts configured for channel: {channel}")

        prompt = SCRIPT_PROMPT_TEMPLATE.format(
            topic=topic,
            channel_type=channel.value,
            emotion_markers=", ".join(prompts["emotion_markers"]),
        )

        result = await self._client.generate_json(
            prompt=prompt,
            system=prompts["script_system"],
            temperature=0.7,
            max_tokens=8192,
        )

        return Script(
            title=result.get("title", topic[:60]),
            hook=result.get("hook", ""),
            body=result.get("body", ""),
            cta=result.get("cta", ""),
            emotion_markers=result.get("emotion_markers", []),
            channel=channel,
            keywords=result.get("keywords", []),
        )

    async def validate_script(self, script: Script) -> tuple[bool, list[str]]:
        errors: list[str] = []

        if not script.hook or len(script.hook) < 20:
            errors.append("Hook is missing or too short (min 20 chars)")

        if not script.body or len(script.body) < 500:
            errors.append("Body is missing or too short (min 500 chars)")

        if not script.cta or len(script.cta) < 10:
            errors.append("CTA is missing or too short (min 10 chars)")

        if len(script.title) > 100:
            errors.append("Title is too long (max 100 chars)")

        if not script.emotion_markers:
            errors.append("No emotion markers found")

        full_script = f"{script.hook} {script.body} {script.cta}"
        word_count = len(full_script.split())
        
        if word_count < 800:
            errors.append(f"Script too short: {word_count} words (min 800)")
        elif word_count > 2500:
            errors.append(f"Script too long: {word_count} words (max 2500)")

        profanity_patterns = [r'\b(fuck|shit|damn|ass)\b']
        for pattern in profanity_patterns:
            if re.search(pattern, full_script, re.IGNORECASE):
                errors.append("Script contains profanity (demonetization risk)")
                break

        has_section_breaks = "[SECTION]" in script.body or "\n\n" in script.body
        if not has_section_breaks:
            errors.append("Body lacks clear section breaks")

        return len(errors) == 0, errors


def get_script_generator(provider: str = "anthropic", **kwargs) -> ScriptGeneratorImpl:
    client = get_llm_client(provider, **kwargs)
    return ScriptGeneratorImpl(llm_client=client)
