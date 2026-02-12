import asyncio
import hashlib
import re
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from config import get_settings
from src.core.exceptions import ThumbnailError
from src.core.interfaces import ThumbnailGenerator as IThumbnailGenerator
from src.core.models import ChannelType, Thumbnail
from src.services.thumbnail.styles import (
    TextPosition,
    TextStyle,
    ThumbnailStyle,
    get_styles_for_channel,
)

THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720
VARIANT_LABELS = ["A", "B", "C", "D", "E"]


class ThumbnailGenerator(IThumbnailGenerator):
    def __init__(self) -> None:
        self.settings = get_settings()
        self._font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

    async def generate(
        self,
        title: str,
        channel: ChannelType,
        output_path: Path,
        style: ThumbnailStyle | None = None,
        variant: str = "A",
    ) -> Thumbnail:
        styles = get_styles_for_channel(channel)
        if style is None:
            style = styles[0]

        try:
            base_image = await self._generate_base_image(title, style)
            base_image = self._apply_image_effects(base_image, style)
            display_text = self._extract_display_text(title, style.text_style.max_words)
            final_image = self._add_text_overlay(base_image, display_text, style.text_style)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            final_image.save(str(output_path), "JPEG", quality=95)

            return Thumbnail(
                path=output_path,
                title_text=title,
                variant=variant,
            )
        except Exception as e:
            raise ThumbnailError(f"Failed to generate thumbnail: {e}") from e

    async def generate_variants(
        self,
        title: str,
        channel: ChannelType,
        output_dir: Path,
        count: int = 3,
    ) -> list[Thumbnail]:
        styles = get_styles_for_channel(channel)
        count = min(count, len(styles), len(VARIANT_LABELS))

        tasks = []
        for i in range(count):
            variant = VARIANT_LABELS[i]
            filename = self._generate_filename(title, variant)
            output_path = output_dir / filename
            tasks.append(
                self.generate(title, channel, output_path, style=styles[i], variant=variant)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        thumbnails: list[Thumbnail] = []
        for result in results:
            if isinstance(result, Thumbnail):
                thumbnails.append(result)

        if not thumbnails:
            raise ThumbnailError("All thumbnail variants failed to generate")

        return thumbnails

    async def _generate_base_image(self, title: str, style: ThumbnailStyle) -> Image.Image:
        if httpx is None:
            raise ThumbnailError("httpx not installed")

        prompt = style.prompt_template.format(subject=title)
        provider = getattr(self.settings.visual, "default_provider", "replicate")

        if provider == "openai":
            return await self._generate_dalle(prompt)
        return await self._generate_replicate(prompt, style.negative_prompt)

    async def _generate_replicate(self, prompt: str, negative_prompt: str) -> Image.Image:
        if httpx is None:
            raise ThumbnailError("httpx not installed")

        api_key = self.settings.visual.replicate_api_token.get_secret_value()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Token {api_key}"},
                json={
                    "version": "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                    "input": {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "width": THUMBNAIL_WIDTH,
                        "height": THUMBNAIL_HEIGHT,
                        "num_outputs": 1,
                        "guidance_scale": 7.5,
                        "num_inference_steps": 30,
                    },
                },
            )
            response.raise_for_status()
            prediction = response.json()

            prediction_id = prediction["id"]
            for _ in range(60):
                await asyncio.sleep(2)
                poll_response = await client.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {api_key}"},
                )
                poll_response.raise_for_status()
                result = poll_response.json()

                if result["status"] == "succeeded":
                    image_url = result["output"][0]
                    img_response = await client.get(image_url)
                    img_response.raise_for_status()
                    return Image.open(BytesIO(img_response.content)).convert("RGB")
                elif result["status"] == "failed":
                    raise ThumbnailError(f"Replicate generation failed: {result.get('error')}")

            raise ThumbnailError("Replicate generation timed out")

    async def _generate_dalle(self, prompt: str) -> Image.Image:
        if httpx is None:
            raise ThumbnailError("httpx not installed")

        api_key = self.settings.llm.openai_api_key.get_secret_value()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "size": "1792x1024",
                    "quality": "standard",
                    "n": 1,
                },
            )
            response.raise_for_status()
            result = response.json()
            image_url = result["data"][0]["url"]

            img_response = await client.get(image_url)
            img_response.raise_for_status()
            img = Image.open(BytesIO(img_response.content)).convert("RGB")
            return img.resize((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)

    def _apply_image_effects(self, img: Image.Image, style: ThumbnailStyle) -> Image.Image:
        if style.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(style.brightness)

        if style.contrast_boost != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(style.contrast_boost)

        if style.saturation_boost != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(style.saturation_boost)

        if style.overlay_color and style.overlay_opacity > 0:
            overlay = Image.new("RGB", img.size, style.overlay_color)
            img = Image.blend(img, overlay, style.overlay_opacity)

        if style.vignette:
            img = self._apply_vignette(img)

        return img

    def _apply_vignette(self, img: Image.Image) -> Image.Image:
        width, height = img.size
        mask = Image.new("L", (width, height), 255)
        draw = ImageDraw.Draw(mask)

        for i in range(50):
            alpha = int(255 * (1 - i / 50) * 0.5)
            draw.rectangle([i, i, width - i, height - i], outline=alpha)

        mask = mask.filter(ImageFilter.GaussianBlur(radius=50))
        dark = Image.new("RGB", img.size, (0, 0, 0))
        return Image.composite(img, dark, mask)

    def _extract_display_text(self, title: str, max_words: int) -> str:
        title = re.sub(r"[^\w\s]", "", title)
        words = title.split()

        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "and",
            "but",
            "if",
            "or",
            "because",
            "until",
            "while",
            "this",
            "that",
            "these",
            "those",
        }

        key_words = []
        for word in words:
            if word.lower() not in stop_words:
                key_words.append(word)
            if len(key_words) >= max_words:
                break

        if not key_words and words:
            key_words = words[:max_words]

        return " ".join(key_words)

    def _get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        cache_key = (font_name, size)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font_paths = [
            f"/usr/share/fonts/truetype/{font_name.lower()}.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            f"/usr/share/fonts/TTF/{font_name}.ttf",
            f"/System/Library/Fonts/{font_name}.ttf",
            f"C:/Windows/Fonts/{font_name.lower()}.ttf",
        ]

        for path in font_paths:
            try:
                font = ImageFont.truetype(path, size)
                self._font_cache[cache_key] = font
                return font
            except OSError:
                continue

        return ImageFont.load_default()

    def _add_text_overlay(self, img: Image.Image, text: str, style: TextStyle) -> Image.Image:
        if style.uppercase:
            text = text.upper()

        draw = ImageDraw.Draw(img)
        font = self._get_font(style.font_name, style.font_size)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])

        padding = 40
        max_width = THUMBNAIL_WIDTH - (padding * 2)

        if text_width > max_width:
            words = text.split()
            lines: list[str] = []
            current_line: list[str] = []

            for word in words:
                test_line = " ".join(current_line + [word])
                test_bbox = draw.textbbox((0, 0), test_line, font=font)
                test_width = int(test_bbox[2] - test_bbox[0])

                if test_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(" ".join(current_line))

            text = "\n".join(lines)
            bbox = draw.multiline_textbbox((0, 0), text, font=font)
            text_width = int(bbox[2] - bbox[0])
            text_height = int(bbox[3] - bbox[1])

        x, y = self._calculate_text_position(style.position, text_width, text_height, padding)

        shadow_x = x + style.shadow_offset[0]
        shadow_y = y + style.shadow_offset[1]
        draw.multiline_text(
            (shadow_x, shadow_y),
            text,
            font=font,
            fill=style.shadow_color,
            align="center",
            spacing=style.line_spacing,
        )

        for offset_x in range(-style.stroke_width, style.stroke_width + 1):
            for offset_y in range(-style.stroke_width, style.stroke_width + 1):
                if offset_x == 0 and offset_y == 0:
                    continue
                draw.multiline_text(
                    (x + offset_x, y + offset_y),
                    text,
                    font=font,
                    fill=style.stroke_color,
                    align="center",
                    spacing=style.line_spacing,
                )

        draw.multiline_text(
            (x, y),
            text,
            font=font,
            fill=style.color,
            align="center",
            spacing=style.line_spacing,
        )

        return img

    def _calculate_text_position(
        self, position: TextPosition, text_width: int, text_height: int, padding: int
    ) -> tuple[int, int]:
        center_x = (THUMBNAIL_WIDTH - text_width) // 2
        center_y = (THUMBNAIL_HEIGHT - text_height) // 2

        positions = {
            TextPosition.TOP: (center_x, padding),
            TextPosition.CENTER: (center_x, center_y),
            TextPosition.BOTTOM: (center_x, THUMBNAIL_HEIGHT - text_height - padding),
            TextPosition.TOP_LEFT: (padding, padding),
            TextPosition.BOTTOM_RIGHT: (
                THUMBNAIL_WIDTH - text_width - padding,
                THUMBNAIL_HEIGHT - text_height - padding,
            ),
        }

        return positions.get(position, (center_x, center_y))

    def _generate_filename(self, title: str, variant: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[\s_]+", "-", slug)[:30]
        hash_suffix = hashlib.md5(title.encode()).hexdigest()[:6]
        return f"thumb_{slug}_{variant}_{hash_suffix}.jpg"
