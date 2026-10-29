
"""Shared configuration loading for segclip."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CHAR_LIMIT = 30_000
CONFIG_PATH = Path(__file__).resolve().parents[2] / "segclip.toml"

DEFAULT_MARKERS = {
    "start_sequence": "<|SEGCLIP_START|>",
    "start_segment": "<|SEGCLIP_SEGMENT|>",
    "end_segment": "<|SEGCLIP_END_SEGMENT|>",
    "end_sequence": "<|SEGCLIP_END|>",
}

DEFAULT_INSTRUCTION = (
    "The following segments form one ordered input. "
    "Retain and assemble them in order; wait until the end-of-sequence "
    "marker before responding."
)


@dataclass(frozen=True)
class SegclipConfig:
    char_limit: int
    start_sequence: str
    start_segment: str
    end_segment: str
    end_sequence: str
    start_sequence_instruction: str


def load_config(path: Path = CONFIG_PATH) -> SegclipConfig:
    """Load and validate segclip configuration."""
    try:
        with path.open("rb") as config_file:
            raw = tomllib.load(config_file)
    except FileNotFoundError:
        if path != CONFIG_PATH:
            raise ValueError(f"Configuration file not found: {path}") from None
        raw = {}
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"Cannot read configuration {path}: {exc}") from exc

    char_limit = raw.get("char_limit", DEFAULT_CHAR_LIMIT)
    if isinstance(char_limit, bool) or not isinstance(char_limit, int):
        raise TypeError("'char_limit' must be an integer.")
    if char_limit < 1:
        raise ValueError("'char_limit' must be a positive integer.")

    raw_markers = raw.get("markers", {})
    if not isinstance(raw_markers, dict):
        raise TypeError("'markers' must be a TOML table.")

    markers = {
        name: raw_markers.get(name, default)
        for name, default in DEFAULT_MARKERS.items()
    }

    for name, value in markers.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Marker '{name}' must be a non-empty string.")

    if len(set(markers.values())) != len(markers):
        raise ValueError("All four marker values must be unique.")

    raw_instructions = raw.get("instructions", {})
    if not isinstance(raw_instructions, dict):
        raise TypeError("'instructions' must be a TOML table.")

    instruction = raw_instructions.get(
        "start_sequence",
        DEFAULT_INSTRUCTION,
    )
    if not isinstance(instruction, str):
        raise TypeError("'instructions.start_sequence' must be a string.")

    return SegclipConfig(
        char_limit=char_limit,
        start_sequence=markers["start_sequence"],
        start_segment=markers["start_segment"],
        end_segment=markers["end_segment"],
        end_sequence=markers["end_sequence"],
        start_sequence_instruction=instruction.strip(),
    )
