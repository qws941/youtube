from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Any, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from src.core.models import Script


@dataclass
class SubtitleEntry:
    index: int
    start_time: float
    end_time: float
    text: str

    def to_srt(self) -> str:
        return f"{self.index}\n{self._format_time(self.start_time)} --> {self._format_time(self.end_time)}\n{self.text}\n"

    @staticmethod
    def _format_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class SubtitleGenerator:
    WORDS_PER_MINUTE = 150
    MAX_CHARS_PER_LINE = 42
    MAX_LINES = 2
    MIN_DURATION = 1.0
    MAX_DURATION = 7.0

    def __init__(self, words_per_minute: int = 150):
        self.words_per_minute = words_per_minute
        self._seconds_per_word = 60.0 / words_per_minute

    def generate_srt(self, script: Any, output_path: Path) -> Path:
        entries = self._script_to_entries(script)
        srt_content = self._entries_to_srt(entries)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(srt_content, encoding="utf-8")
        return output_path

    def generate_from_text(self, text: str, output_path: Path) -> Path:
        entries = self._text_to_entries(text)
        srt_content = self._entries_to_srt(entries)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(srt_content, encoding="utf-8")
        return output_path

    def generate_from_segments(
        self,
        segments: list[dict],
        output_path: Path,
    ) -> Path:
        entries = []
        for i, seg in enumerate(segments, 1):
            entries.append(SubtitleEntry(
                index=i,
                start_time=seg["start"],
                end_time=seg["end"],
                text=self._wrap_text(seg["text"]),
            ))
        srt_content = self._entries_to_srt(entries)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(srt_content, encoding="utf-8")
        return output_path

    def _script_to_entries(self, script: Any) -> list[SubtitleEntry]:
        text = self._extract_text_from_script(script)
        return self._text_to_entries(text)

    def _extract_text_from_script(self, script: Any) -> str:
        if hasattr(script, "scenes") and script.scenes:
            parts = []
            for scene in script.scenes:
                if hasattr(scene, "narration"):
                    parts.append(scene.narration)
                elif hasattr(scene, "text"):
                    parts.append(scene.text)
                else:
                    parts.append(str(scene))
            return " ".join(parts)

        if hasattr(script, "content") and script.content:
            return script.content

        if hasattr(script, "text") and script.text:
            return script.text

        if hasattr(script, "full_text") and script.full_text:
            return script.full_text

        return str(script)

    def _text_to_entries(self, text: str) -> list[SubtitleEntry]:
        entries = []
        current_time = 0.0
        index = 1

        sentences = self._split_sentences(text)

        for sentence in sentences:
            if not sentence.strip():
                continue

            duration = self._calculate_duration(sentence)
            wrapped = self._wrap_text(sentence)

            entries.append(SubtitleEntry(
                index=index,
                start_time=current_time,
                end_time=current_time + duration,
                text=wrapped,
            ))

            current_time += duration
            index += 1

        return entries

    def _split_sentences(self, text: str) -> list[str]:
        text = re.sub(r"\s+", " ", text.strip())
        sentences = re.split(r"(?<=[.!?])\s+", text)
        result = []

        for sentence in sentences:
            words = sentence.split()
            if len(words) > 15:
                chunks = self._chunk_long_sentence(words)
                result.extend(chunks)
            else:
                result.append(sentence)

        return result

    def _chunk_long_sentence(self, words: list[str]) -> list[str]:
        chunks = []
        current_chunk: list[str] = []
        word_count = 0

        for word in words:
            current_chunk.append(word)
            word_count += 1

            if word_count >= 10 and (word.endswith(",") or word_count >= 12):
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                word_count = 0

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _calculate_duration(self, text: str) -> float:
        word_count = len(text.split())
        duration = word_count * self._seconds_per_word
        return max(self.MIN_DURATION, min(duration, self.MAX_DURATION))

    def _wrap_text(self, text: str) -> str:
        text = text.strip()
        if len(text) <= self.MAX_CHARS_PER_LINE:
            return text

        words = text.split()
        lines: list[str] = []
        current_line: list[str] = []
        current_length = 0

        for word in words:
            word_len = len(word)
            if current_length + word_len + (1 if current_line else 0) > self.MAX_CHARS_PER_LINE:
                if current_line:
                    lines.append(" ".join(current_line))
                    if len(lines) >= self.MAX_LINES:
                        remaining = words[words.index(word):]
                        lines[-1] += " " + " ".join(remaining)
                        break
                    current_line = [word]
                    current_length = word_len
                else:
                    lines.append(word)
                    current_line = []
                    current_length = 0
            else:
                current_line.append(word)
                current_length += word_len + (1 if len(current_line) > 1 else 0)

        if current_line and len(lines) < self.MAX_LINES:
            lines.append(" ".join(current_line))

        return "\n".join(lines[:self.MAX_LINES])

    def _entries_to_srt(self, entries: list[SubtitleEntry]) -> str:
        return "\n".join(entry.to_srt() for entry in entries)


class SubtitleStyle:
    DEFAULT = {
        "fontname": "Arial",
        "fontsize": 24,
        "primary_color": "&HFFFFFF",
        "outline_color": "&H000000",
        "outline": 2,
        "shadow": 1,
        "alignment": 2,
        "margin_v": 50,
    }

    @classmethod
    def to_ffmpeg_filter(cls, style: Optional[dict] = None) -> str:
        s = {**cls.DEFAULT, **(style or {})}
        return (
            f"subtitles=filename='{{srt_path}}':force_style='"
            f"FontName={s['fontname']},"
            f"FontSize={s['fontsize']},"
            f"PrimaryColour={s['primary_color']},"
            f"OutlineColour={s['outline_color']},"
            f"Outline={s['outline']},"
            f"Shadow={s['shadow']},"
            f"Alignment={s['alignment']},"
            f"MarginV={s['margin_v']}'"
        )

    @classmethod
    def get_ffmpeg_args(cls, srt_path: Path, style: Optional[dict] = None) -> str:
        s = {**cls.DEFAULT, **(style or {})}
        srt_escaped = str(srt_path).replace(":", "\\:").replace("'", "\\'")
        return (
            f"subtitles='{srt_escaped}':force_style='"
            f"FontName={s['fontname']},"
            f"FontSize={s['fontsize']},"
            f"PrimaryColour={s['primary_color']},"
            f"OutlineColour={s['outline_color']},"
            f"Outline={s['outline']},"
            f"Shadow={s['shadow']},"
            f"Alignment={s['alignment']},"
            f"MarginV={s['margin_v']}'"
        )
