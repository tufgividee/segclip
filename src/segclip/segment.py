
"""Lossless text segmentation with natural boundary preference."""

import re
from dataclasses import dataclass

from segclip.config import SegclipConfig, load_config

# Sentence punctuation, optional closing quotes/brackets, and whitespace.
# The whitespace stays with the preceding segment.
_SENTENCE_END = re.compile(r"""[.!?]+["')\]]*\s+""")

CONCLUSION = """<CONTEXT_CONCLUSION>
All segments in this context sequence have now been provided.
The complete source context is available by combining the payloads in
segment order. The headers, footers, and this conclusion are metadata,
not part of the original source. You may now analyze the complete context.
<END_CONTEXT_CONCLUSION>"""


@dataclass(frozen=True)
class Segment:
    index: int
    total: int
    payload: str
    text: str


@dataclass(frozen=True)
class Segmentation:
    source_characters: int
    payload_limit: int
    segments: tuple[Segment, ...]

    @property
    def total_clipboard_characters(self) -> int:
        return sum(len(segment.text) for segment in self.segments)


def _best_boundary(text: str, start: int, end: int) -> int:
    """Choose a natural boundary within text[start:end], if possible.

    Preference:
    1. Newline / line boundary.
    2. Sentence boundary.
    3. Other whitespace boundary.
    4. Hard character limit.
    """
    window = text[start:end]

    newline = window.rfind("\n")
    if newline >= 0:
        return start + newline + 1

    sentence_boundaries = [
        match.end() for match in _SENTENCE_END.finditer(window)
    ]
    if sentence_boundaries:
        return start + sentence_boundaries[-1]

    whitespace = max(
        window.rfind(" "),
        window.rfind("\t"),
        window.rfind("\r"),
    )
    if whitespace >= 0:
        return start + whitespace + 1

    return end


def split_payload(text: str, char_limit: int) -> list[str]:
    """Split text losslessly into payloads no longer than char_limit."""
    if isinstance(char_limit, bool) or not isinstance(char_limit, int):
        raise TypeError("char_limit must be an integer")
    if char_limit < 1:
        raise ValueError("char_limit must be a positive integer")

    if len(text) <= char_limit:
        return [text]

    parts: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + char_limit, len(text))

        if end == len(text):
            parts.append(text[start:end])
            break

        boundary = _best_boundary(text, start, end)
        if boundary <= start:
            boundary = end

        parts.append(text[start:boundary])
        start = boundary

    if "".join(parts) != text:
        raise AssertionError("Segmentation failed to preserve source content")

    if any(len(part) > char_limit for part in parts):
        raise AssertionError("A payload exceeds the configured character limit")

    return parts



def format_segments(
    text: str,
    char_limit: int | None = None,
    *,
    session_id: str | None = None,
    config: SegclipConfig | None = None,
) -> Segmentation:
    """Format ordered segments using the configured four-marker protocol.

    Text that fits in one payload remains unchanged.
    """
    del session_id  # Retained temporarily for backward compatibility.

    if config is None:
        config = load_config()

    effective_limit = (
        config.char_limit if char_limit is None else char_limit
    )
    payloads = split_payload(text, effective_limit)

    if len(payloads) == 1:
        return Segmentation(
            source_characters=len(text),
            payload_limit=effective_limit,
            segments=(
                Segment(
                    index=1,
                    total=1,
                    payload=text,
                    text=text,
                ),
            ),
        )

    total = len(payloads)
    segments: list[Segment] = []

    for index, payload in enumerate(payloads, start=1):
        parts: list[str] = []

        if index == 1:
            parts.append(config.start_sequence)
            if config.start_sequence_instruction:
                parts.append(config.start_sequence_instruction)
            parts.append("")

        parts.append(f"{config.start_segment}{index}/{total}")
        parts.append(payload)
        parts.append(config.end_segment)

        if index == total:
            parts.append(config.end_sequence)

        formatted = "\n".join(parts)

        # Confirm the original payload is present unchanged.
        payload_start = formatted.index(f"{config.start_segment}{index}/{total}\n")
        payload_start += len(f"{config.start_segment}{index}/{total}\n")

        if formatted[payload_start:payload_start + len(payload)] != payload:
            raise AssertionError("Formatted segment changed its source payload")

        segments.append(
            Segment(
                index=index,
                total=total,
                payload=payload,
                text=formatted,
            )
        )

    if "".join(segment.payload for segment in segments) != text:
        raise AssertionError("Formatted segments do not reconstruct the source")

    return Segmentation(
        source_characters=len(text),
        payload_limit=effective_limit,
        segments=tuple(segments),
    )
