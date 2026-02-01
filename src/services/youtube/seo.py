from __future__ import annotations

import re
from typing import Any

from src.core.models import ChannelType

CHANNEL_KEYWORDS: dict[ChannelType, list[str]] = {
    ChannelType.HORROR: [
        "공포",
        "미스터리",
        "무서운",
        "심령",
        "귀신",
        "소름",
        "실화",
        "horror",
        "scary",
        "creepy",
        "ghost",
        "paranormal",
        "mystery",
    ],
    ChannelType.FACTS: [
        "과학",
        "팩트",
        "사실",
        "놀라운",
        "충격",
        "진실",
        "상식",
        "facts",
        "science",
        "amazing",
        "truth",
        "mind-blowing",
    ],
    ChannelType.FINANCE: [
        "투자",
        "주식",
        "부동산",
        "돈",
        "재테크",
        "경제",
        "수익",
        "배당",
        "investing",
        "money",
        "finance",
        "stocks",
        "wealth",
        "passive income",
    ],
}

CHANNEL_HASHTAGS: dict[ChannelType, list[str]] = {
    ChannelType.HORROR: ["#공포", "#미스터리", "#소름", "#실화", "#Horror", "#Scary"],
    ChannelType.FACTS: ["#과학", "#팩트", "#충격", "#Facts", "#Science", "#Amazing"],
    ChannelType.FINANCE: ["#투자", "#재테크", "#부자", "#Finance", "#Money", "#Investing"],
}


class SEOOptimizer:
    def __init__(self, channel_type: ChannelType) -> None:
        self._channel_type = channel_type
        self._keywords = CHANNEL_KEYWORDS.get(channel_type, [])
        self._hashtags = CHANNEL_HASHTAGS.get(channel_type, [])

    def optimize_title(
        self,
        raw_title: str,
        max_length: int = 60,
        add_brackets: bool = True,
    ) -> str:
        title = raw_title.strip()
        title = self._remove_extra_spaces(title)

        keywords_in_title = [kw for kw in self._keywords if kw.lower() in title.lower()]

        if not keywords_in_title and self._keywords:
            primary_keyword = self._keywords[0]
            title = f"[{primary_keyword}] {title}" if add_brackets else f"{primary_keyword} {title}"

        if len(title) > max_length:
            title = self._truncate_smart(title, max_length)

        title = self._add_engagement_hook(title, max_length)

        return title[:max_length].strip()

    def _truncate_smart(self, title: str, max_length: int) -> str:
        if len(title) <= max_length:
            return title

        truncated = title[: max_length - 3]

        for sep in ["...", " - ", ": ", " | "]:
            if sep in truncated:
                truncated = truncated.rsplit(sep, 1)[0]
                break
        else:
            last_space = truncated.rfind(" ")
            if last_space > max_length // 2:
                truncated = truncated[:last_space]

        return truncated + "..."

    def _add_engagement_hook(self, title: str, max_length: int) -> str:
        hooks = ["?!", "...", "!"]
        has_hook = any(title.endswith(h) for h in hooks)

        if not has_hook and len(title) < max_length - 2:
            if "?" in title or "왜" in title or "어떻게" in title:
                title = title.rstrip("?.!") + "?"

        return title

    def _remove_extra_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def generate_description(
        self,
        script: Any,
        channel_name: str | None = None,
        channel_url: str | None = None,
        include_timestamps: bool = True,
        include_hashtags: bool = True,
    ) -> str:
        parts: list[str] = []

        hook = self._extract_hook(script)
        if hook:
            parts.append(hook)
            parts.append("")

        if include_timestamps:
            scenes = getattr(script, "scenes", None)
            if scenes:
                timestamps = self._generate_timestamps(script)
                if timestamps:
                    parts.append("⏱️ 타임스탬프")
                    parts.extend(timestamps)
                    parts.append("")

        if channel_name or channel_url:
            parts.append("📺 채널 정보")
            if channel_name:
                parts.append(f"채널명: {channel_name}")
            if channel_url:
                parts.append(f"구독하기: {channel_url}")
            parts.append("")

        parts.append("🔔 좋아요, 구독, 알림설정 부탁드립니다!")
        parts.append("")

        if include_hashtags:
            hashtags = " ".join(self._hashtags[:6])
            parts.append(hashtags)

        description = "\n".join(parts)
        return description[:5000]

    def _extract_hook(self, script: Any) -> str:
        hook = getattr(script, "hook", None)
        if hook:
            return str(hook)[:200]

        scenes = getattr(script, "scenes", None)
        if scenes and len(scenes) > 0:
            first_scene = scenes[0]
            narration = getattr(first_scene, "narration", None)
            if narration:
                return str(narration)[:200] + "..."
        return ""

    def _generate_timestamps(self, script: Any) -> list[str]:
        timestamps: list[str] = []
        scenes = getattr(script, "scenes", None)
        if not scenes:
            return timestamps

        current_time = 0
        for scene in scenes:
            title = getattr(scene, "title", None)
            if title:
                time_str = self._format_timestamp(current_time)
                timestamps.append(f"{time_str} {title}")

            duration = getattr(scene, "duration", 60)
            current_time += duration

        return timestamps[:10]

    def _format_timestamp(self, seconds: int) -> str:
        minutes = seconds // 60
        secs = seconds % 60
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def generate_tags(
        self,
        script: Any,
        max_total_chars: int = 500,
        max_tags: int = 30,
    ) -> list[str]:
        tags: list[str] = []

        tags.extend(self._keywords[:5])

        title = getattr(script, "title", None)
        if title:
            title_words = self._extract_keywords_from_text(str(title))
            tags.extend(title_words[:5])

        topic = getattr(script, "topic", None)
        if topic:
            tags.append(str(topic))

        keywords = getattr(script, "keywords", None)
        if keywords:
            tags.extend(list(keywords)[:10])

        extra_tags = self._get_trending_tags()
        tags.extend(extra_tags)

        tags = self._deduplicate_tags(tags)
        tags = self._filter_tags(tags, max_total_chars, max_tags)

        return tags

    def _extract_keywords_from_text(self, text: str) -> list[str]:
        cleaned = re.sub(r"[^\w\s가-힣]", " ", text)
        words = cleaned.split()
        keywords = [w for w in words if len(w) >= 2 and not w.isdigit()]
        return keywords[:10]

    def _get_trending_tags(self) -> list[str]:
        base_tags: dict[ChannelType, list[str]] = {
            ChannelType.HORROR: [
                "무서운이야기",
                "공포영상",
                "심령체험",
                "괴담",
                "horror story",
            ],
            ChannelType.FACTS: [
                "신기한사실",
                "과학영상",
                "상식",
                "교양",
                "facts you didnt know",
            ],
            ChannelType.FINANCE: [
                "주식추천",
                "부동산투자",
                "재테크방법",
                "경제공부",
                "money tips",
            ],
        }
        return base_tags.get(self._channel_type, [])

    def _deduplicate_tags(self, tags: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for tag in tags:
            tag_lower = tag.lower().strip()
            if tag_lower and tag_lower not in seen:
                seen.add(tag_lower)
                result.append(tag.strip())
        return result

    def _filter_tags(
        self,
        tags: list[str],
        max_chars: int,
        max_count: int,
    ) -> list[str]:
        result: list[str] = []
        total_chars = 0

        for tag in tags:
            if len(result) >= max_count:
                break
            tag_len = len(tag)
            if total_chars + tag_len + 1 > max_chars:
                continue
            result.append(tag)
            total_chars += tag_len + 1

        return result

    def optimize_all(
        self,
        script: Any,
        raw_title: str,
        channel_name: str | None = None,
        channel_url: str | None = None,
    ) -> dict[str, Any]:
        return {
            "title": self.optimize_title(raw_title),
            "description": self.generate_description(
                script,
                channel_name=channel_name,
                channel_url=channel_url,
            ),
            "tags": self.generate_tags(script),
        }
