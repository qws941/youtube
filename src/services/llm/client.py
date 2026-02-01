from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
import json
import time

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import get_settings
from src.core.exceptions import LLMError, LLMRateLimitError


# OpenCode auth.json location
OPENCODE_AUTH_PATH = Path.home() / ".local" / "share" / "opencode" / "auth.json"


def get_opencode_token(provider: str) -> str | None:
    """Read OAuth access token from OpenCode auth.json.
    
    Args:
        provider: "anthropic" or "openai"
    
    Returns:
        Access token string or None if not found/expired
    """
    if not OPENCODE_AUTH_PATH.exists():
        return None
    
    try:
        with open(OPENCODE_AUTH_PATH) as f:
            auth_data = json.load(f)
        
        if provider not in auth_data:
            return None
        
        provider_data = auth_data[provider]
        access_token = provider_data.get("access")
        expires = provider_data.get("expires", 0)
        
        # Check if token is expired (with 5 min buffer)
        if expires > 0 and expires < (time.time() * 1000 + 300000):
            return None
        
        return access_token
    except (json.JSONDecodeError, KeyError, OSError):
        return None


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        pass

    @abstractmethod
    async def generate_json(self, prompt: str, system: str | None = None, **kwargs) -> dict[str, Any]:
        pass


def _retry_decorator():
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((LLMRateLimitError,)),
        reraise=True,
    )


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        settings = get_settings()
        resolved_key = api_key
        if not resolved_key and settings.llm.use_opencode_auth:
            resolved_key = get_opencode_token("anthropic")
        if not resolved_key:
            resolved_key = settings.llm.anthropic_api_key.get_secret_value()
        self._client = AsyncAnthropic(api_key=resolved_key)
        self._model = model
        self._max_tokens = 4096

    @_retry_decorator()
    async def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        try:
            messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=kwargs.get("max_tokens", self._max_tokens),
                system=system or "",
                messages=messages,  # type: ignore[arg-type]
                temperature=kwargs.get("temperature", 0.7),
            )
            content_block = response.content[0]
            return content_block.text if hasattr(content_block, "text") else str(content_block)  # type: ignore[union-attr]
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise LLMRateLimitError(f"Anthropic rate limit: {e}") from e
            raise LLMError(f"Anthropic generation failed: {e}") from e

    @_retry_decorator()
    async def generate_json(self, prompt: str, system: str | None = None, **kwargs) -> dict[str, Any]:
        json_system = (system or "") + "\n\nYou must respond with valid JSON only. No markdown, no explanation."
        try:
            text = await self.generate(prompt, system=json_system, **kwargs)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse JSON response: {e}") from e


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        settings = get_settings()
        resolved_key = api_key
        if not resolved_key and settings.llm.use_opencode_auth:
            resolved_key = get_opencode_token("openai")
        if not resolved_key:
            resolved_key = settings.llm.openai_api_key.get_secret_value()
        self._client = AsyncOpenAI(api_key=resolved_key)
        self._model = model
        self._max_tokens = 4096

    @_retry_decorator()
    async def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self._max_tokens),
                temperature=kwargs.get("temperature", 0.7),
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise LLMRateLimitError(f"OpenAI rate limit: {e}") from e
            raise LLMError(f"OpenAI generation failed: {e}") from e

    @_retry_decorator()
    async def generate_json(self, prompt: str, system: str | None = None, **kwargs) -> dict[str, Any]:
        json_system = (system or "") + "\n\nYou must respond with valid JSON only. No markdown, no explanation."
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": json_system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=kwargs.get("max_tokens", self._max_tokens),
                temperature=kwargs.get("temperature", 0.7),
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content or "{}"
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse JSON response: {e}") from e
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise LLMRateLimitError(f"OpenAI rate limit: {e}") from e
            raise LLMError(f"OpenAI JSON generation failed: {e}") from e


def get_llm_client(provider: str = "anthropic", **kwargs) -> LLMClient:
    providers = {
        "anthropic": AnthropicClient,
        "openai": OpenAIClient,
    }
    if provider not in providers:
        raise LLMError(f"Unknown provider: {provider}. Available: {list(providers.keys())}")
    return providers[provider](**kwargs)
