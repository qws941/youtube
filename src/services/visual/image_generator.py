from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

import httpx
import replicate
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import get_settings
from src.core.interfaces import ImageGenerator as ImageGeneratorABC
from src.core.models import VisualAsset, ChannelType
from src.core.exceptions import ImageGenerationError


CHANNEL_STYLE_PRESETS: dict[ChannelType, dict[str, Any]] = {
    ChannelType.HORROR: {
        "style_suffix": "dark atmosphere, cinematic lighting, moody shadows, dramatic contrast, horror aesthetic, eerie fog, desaturated colors",
        "negative_prompt": "bright, cheerful, cartoon, anime, colorful, happy",
        "cfg_scale": 8.0,
    },
    ChannelType.FACTS: {
        "style_suffix": "bright lighting, clean composition, infographic style, modern design, sharp details, vibrant colors, educational aesthetic",
        "negative_prompt": "dark, gloomy, horror, scary, blurry, messy",
        "cfg_scale": 7.0,
    },
    ChannelType.FINANCE: {
        "style_suffix": "professional photography, corporate aesthetic, modern office, clean lines, business style, stock photo quality, sophisticated lighting",
        "negative_prompt": "cartoon, anime, childish, messy, unprofessional, dark",
        "cfg_scale": 7.5,
    },
}

DEFAULT_STYLE = CHANNEL_STYLE_PRESETS[ChannelType.FACTS]


class ImageGenerator(ImageGeneratorABC):
    def __init__(self) -> None:
        self.settings = get_settings()
        self._openai: AsyncOpenAI | None = None
        self._http_client: httpx.AsyncClient | None = None

    async def _get_openai(self) -> AsyncOpenAI:
        if self._openai is None:
            self._openai = AsyncOpenAI(api_key=self.settings.llm.openai_api_key.get_secret_value())
        return self._openai

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=300.0)
        return self._http_client

    def _get_style_preset(self, channel_type: ChannelType | None) -> dict[str, Any]:
        if channel_type is None:
            return DEFAULT_STYLE
        return CHANNEL_STYLE_PRESETS.get(channel_type, DEFAULT_STYLE)

    def _enhance_prompt(self, prompt: str, channel_type: ChannelType | None) -> str:
        style = self._get_style_preset(channel_type)
        return f"{prompt}, {style['style_suffix']}, 16:9 aspect ratio, 4K resolution, photorealistic"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
        reraise=True,
    )
    async def _generate_replicate_sdxl(
        self,
        prompt: str,
        output_path: Path,
        channel_type: ChannelType | None = None,
        **kwargs: Any,
    ) -> VisualAsset:
        style = self._get_style_preset(channel_type)
        enhanced_prompt = self._enhance_prompt(prompt, channel_type)

        width = kwargs.get("width", 1920)
        height = kwargs.get("height", 1080)

        output = await asyncio.to_thread(
            replicate.run,
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={
                "prompt": enhanced_prompt,
                "negative_prompt": style["negative_prompt"],
                "width": width,
                "height": height,
                "num_inference_steps": kwargs.get("steps", 30),
                "guidance_scale": style["cfg_scale"],
                "scheduler": "K_EULER",
                "refine": "expert_ensemble_refiner",
                "high_noise_frac": 0.8,
                "num_outputs": 1,
            },
        )

        output_list = list(output) if output else []
        if not output_list:
            raise ImageGenerationError("SDXL returned no output")

        image_url = output_list[0]
        client = await self._get_http_client()
        response = await client.get(image_url)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        return VisualAsset(
            asset_type="image",
            path=output_path,
            prompt=prompt,
            metadata={
                "enhanced_prompt": enhanced_prompt,
                "channel_type": channel_type.value if channel_type else None,
                "width": width,
                "height": height,
                "provider": "replicate_sdxl",
            },
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
        reraise=True,
    )
    async def _generate_dalle3(
        self,
        prompt: str,
        output_path: Path,
        channel_type: ChannelType | None = None,
        **kwargs: Any,
    ) -> VisualAsset:
        enhanced_prompt = self._enhance_prompt(prompt, channel_type)

        openai = await self._get_openai()
        response = await openai.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size="1792x1024",
            quality="hd",
            n=1,
            response_format="b64_json",
        )

        if not response.data or len(response.data) == 0:
            raise ImageGenerationError("DALL-E 3 returned no output")

        b64_json = response.data[0].b64_json
        if b64_json is None:
            raise ImageGenerationError("DALL-E 3 returned no image data")
        image_data = base64.b64decode(b64_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_data)

        return VisualAsset(
            asset_type="image",
            path=output_path,
            prompt=prompt,
            metadata={
                "enhanced_prompt": enhanced_prompt,
                "revised_prompt": response.data[0].revised_prompt,
                "width": 1792,
                "height": 1024,
                "provider": "dalle3",
            },
        )

    async def generate(
        self,
        prompt: str,
        output_path: Path | str,
        **kwargs: Any,
    ) -> VisualAsset:
        output_path = Path(output_path)
        channel_type = kwargs.get("channel_type")

        try:
            return await self._generate_replicate_sdxl(prompt, output_path, channel_type, **kwargs)
        except Exception as e:
            try:
                return await self._generate_dalle3(prompt, output_path, channel_type, **kwargs)
            except Exception as fallback_error:
                raise ImageGenerationError(f"All providers failed. SDXL: {e}, DALL-E: {fallback_error}") from fallback_error

    async def generate_batch(
        self,
        prompts: list[str],
        output_dir: Path | str,
        **kwargs: Any,
    ) -> list[VisualAsset]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        for i, prompt in enumerate(prompts):
            output_path = output_dir / f"image_{i:04d}.png"
            tasks.append(self.generate(prompt, output_path, **kwargs))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assets: list[VisualAsset] = []
        errors: list[str] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Image {i}: {result}")
            elif isinstance(result, VisualAsset):
                assets.append(result)

        if errors and not assets:
            raise ImageGenerationError(f"All batch generations failed: {errors}")

        return assets

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        if self._openai:
            await self._openai.close()
            self._openai = None

    async def __aenter__(self) -> ImageGenerator:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
