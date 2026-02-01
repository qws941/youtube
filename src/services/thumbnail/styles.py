from dataclasses import dataclass
from enum import Enum

from src.core.models import ChannelType


class TextPosition(Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"
    TOP_LEFT = "top_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass
class TextStyle:
    font_name: str = "Impact"
    font_size: int = 120
    color: str = "#FFFFFF"
    stroke_color: str = "#000000"
    stroke_width: int = 8
    shadow_offset: tuple[int, int] = (4, 4)
    shadow_color: str = "#000000"
    position: TextPosition = TextPosition.CENTER
    max_words: int = 4
    uppercase: bool = True
    line_spacing: int = 20


@dataclass
class ThumbnailStyle:
    name: str
    prompt_template: str
    negative_prompt: str
    text_style: TextStyle
    overlay_color: str | None = None
    overlay_opacity: float = 0.0
    vignette: bool = False
    saturation_boost: float = 1.0
    contrast_boost: float = 1.0
    brightness: float = 1.0


HORROR_STYLES: list[ThumbnailStyle] = [
    ThumbnailStyle(
        name="horror_dark",
        prompt_template="dark cinematic horror scene, {subject}, abandoned location, fog, volumetric lighting, 8k, hyperrealistic, terrifying atmosphere",
        negative_prompt="cartoon, anime, bright colors, happy, cheerful, low quality",
        text_style=TextStyle(
            color="#FF0000",
            stroke_color="#000000",
            stroke_width=10,
            font_size=130,
            position=TextPosition.CENTER,
        ),
        overlay_color="#000000",
        overlay_opacity=0.3,
        vignette=True,
        contrast_boost=1.2,
    ),
    ThumbnailStyle(
        name="horror_yellow",
        prompt_template="eerie supernatural scene, {subject}, dark shadows, mysterious lighting, horror movie poster style, 8k",
        negative_prompt="cartoon, anime, daylight, cheerful, low quality",
        text_style=TextStyle(
            color="#FFD700",
            stroke_color="#8B0000",
            stroke_width=12,
            font_size=140,
            position=TextPosition.BOTTOM,
        ),
        overlay_color="#1a0000",
        overlay_opacity=0.25,
        vignette=True,
    ),
    ThumbnailStyle(
        name="horror_ghost",
        prompt_template="paranormal ghost apparition, {subject}, dark room, ethereal glow, photorealistic horror, 8k",
        negative_prompt="cartoon, anime, bright, happy, low quality, blurry",
        text_style=TextStyle(
            color="#FFFFFF",
            stroke_color="#660000",
            stroke_width=10,
            font_size=125,
            position=TextPosition.TOP,
        ),
        overlay_color="#000033",
        overlay_opacity=0.2,
        vignette=True,
        brightness=0.9,
    ),
]

FACTS_STYLES: list[ThumbnailStyle] = [
    ThumbnailStyle(
        name="facts_bright",
        prompt_template="surprised person face reaction, {subject}, bright colorful background, studio lighting, high energy, 8k, viral youtube thumbnail style",
        negative_prompt="dark, horror, scary, low quality, blurry",
        text_style=TextStyle(
            color="#FFFFFF",
            stroke_color="#FF4444",
            stroke_width=10,
            font_size=135,
            position=TextPosition.TOP,
        ),
        saturation_boost=1.3,
        contrast_boost=1.15,
    ),
    ThumbnailStyle(
        name="facts_science",
        prompt_template="mind-blowing science visualization, {subject}, glowing elements, cosmic background, educational infographic style, 8k",
        negative_prompt="dark, horror, low quality, cartoon",
        text_style=TextStyle(
            color="#00FFFF",
            stroke_color="#000066",
            stroke_width=8,
            font_size=130,
            position=TextPosition.BOTTOM,
        ),
        overlay_color="#000033",
        overlay_opacity=0.15,
    ),
    ThumbnailStyle(
        name="facts_shocking",
        prompt_template="shocking revelation scene, {subject}, dramatic lighting, bold colors, youtube viral style, 8k, photorealistic",
        negative_prompt="boring, dark, horror, low quality",
        text_style=TextStyle(
            color="#FFFF00",
            stroke_color="#FF0000",
            stroke_width=12,
            font_size=145,
            position=TextPosition.CENTER,
        ),
        saturation_boost=1.4,
        contrast_boost=1.2,
    ),
]

FINANCE_STYLES: list[ThumbnailStyle] = [
    ThumbnailStyle(
        name="finance_pro",
        prompt_template="professional financial visualization, {subject}, stock charts, dollar signs, green arrows up, luxury office background, 8k",
        negative_prompt="cartoon, poor quality, messy, unprofessional",
        text_style=TextStyle(
            font_name="Arial Black",
            color="#00FF00",
            stroke_color="#003300",
            stroke_width=8,
            font_size=120,
            position=TextPosition.TOP,
        ),
        overlay_color="#001a00",
        overlay_opacity=0.1,
    ),
    ThumbnailStyle(
        name="finance_wealth",
        prompt_template="luxury wealth display, {subject}, gold bars, money stacks, expensive lifestyle, cinematic, 8k",
        negative_prompt="poor, cheap, cartoon, low quality",
        text_style=TextStyle(
            color="#FFD700",
            stroke_color="#000000",
            stroke_width=10,
            font_size=130,
            position=TextPosition.BOTTOM,
        ),
        saturation_boost=1.2,
    ),
    ThumbnailStyle(
        name="finance_urgent",
        prompt_template="urgent financial news, {subject}, red and green market indicators, professional trading desk, 8k, dramatic lighting",
        negative_prompt="cartoon, unprofessional, messy, low quality",
        text_style=TextStyle(
            color="#FF0000",
            stroke_color="#FFFFFF",
            stroke_width=10,
            font_size=140,
            position=TextPosition.CENTER,
        ),
        contrast_boost=1.25,
    ),
]

CHANNEL_STYLES: dict[ChannelType, list[ThumbnailStyle]] = {
    ChannelType.HORROR: HORROR_STYLES,
    ChannelType.FACTS: FACTS_STYLES,
    ChannelType.FINANCE: FINANCE_STYLES,
}


def get_styles_for_channel(channel: ChannelType) -> list[ThumbnailStyle]:
    return CHANNEL_STYLES.get(channel, FACTS_STYLES)


def get_style_by_name(channel: ChannelType, style_name: str) -> ThumbnailStyle | None:
    styles = get_styles_for_channel(channel)
    for style in styles:
        if style.name == style_name:
            return style
    return None
