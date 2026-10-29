
"""Command-line interface for segclip."""

import argparse
import os
import sys

from segclip.clipboard import ClipboardError, read_clipboard, write_clipboard
from segclip.config import load_config
from segclip.segment import format_segments


def _read_single_key() -> str:
    """Read one key immediately, without requiring Enter."""
    if os.name == "nt":
        import msvcrt

        return msvcrt.getwch()

    import termios
    import tty

    if not sys.stdin.isatty():
        raise RuntimeError("Interactive controls require a terminal.")

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="segclip",
        description="Interactively segment clipboard text for AI conversations.",
    )
    parser.add_argument(
        "--char-limit",
        type=int,
        default=None,
        help="Maximum payload characters per segment (overrides config.toml).",
    )
    return parser


def run(char_limit: int | None = None) -> int:
    """Read clipboard text, segment it, and copy each segment interactively."""
    try:
        config = load_config()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    effective_limit = config.char_limit if char_limit is None else char_limit

    if (
        isinstance(effective_limit, bool)
        or not isinstance(effective_limit, int)
        or effective_limit < 1
    ):
        print("Error: char_limit must be a positive integer.", file=sys.stderr)
        return 2

    try:
        source = read_clipboard()
    except ClipboardError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not source:
        print("Clipboard is empty or contains no readable text.", file=sys.stderr)
        return 1

    try:
        result = format_segments(source, effective_limit, config=config)
    except (TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    # Text that fits in one segment must remain unchanged.
    if len(result.segments) == 1:
        print(f"Source characters: {result.source_characters:,}")
        print(f"Payload character limit: {result.payload_limit:,}")
        print("Segments: 1")
        print("Text fits within the character limit; clipboard unchanged.")
        return 0

    total = len(result.segments)

    print(f"Source characters: {result.source_characters:,}")
    print(f"Payload character limit: {result.payload_limit:,}")
    print(f"Segments: {total}")
    print(
        "Total clipboard characters across all segments: "
        f"{result.total_clipboard_characters:,}\n"
    )


    # Copy the first segment immediately.
    try:
        write_clipboard(result.segments[0].text)
    except ClipboardError as exc:
        print(
            f"\nError copying segment 1/{total}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        f"Copied segment 1/{total} "
        f"({len(result.segments[0].text):,} clipboard characters)."
    )

    # Wait for Space only for subsequent segments.
    for index, segment in enumerate(result.segments[1:], start=2):
        while True:
            print(
                f"Press SPACE to copy segment {index}/{total}, "
                "or Q / Esc to quit: ",
                end="",
                flush=True,
            )

            try:
                key = _read_single_key()
            except (KeyboardInterrupt, EOFError):
                print("\nStopped.")
                return 0
            except RuntimeError as exc:
                print(f"\nError: {exc}", file=sys.stderr)
                return 2

            if key in ("q", "Q", "\x1b", "\x03"):
                print("\nStopped.")
                return 0

            if key == " ":
                break

            print("\nUnrecognized key. Press Space to copy, or Q to quit.")

        try:
            write_clipboard(segment.text)
        except ClipboardError as exc:
            print(
                f"\nError copying segment {index}/{total}: {exc}",
                file=sys.stderr,
            )
            return 1

        print(
            f"\rCopied segment {index}/{total} "
            f"({len(segment.text):,} clipboard characters)."
        )

    print("All segments copied.")
    return 0



def main() -> int:
    """Run the CLI."""
    args = build_parser().parse_args()
    return run(char_limit=args.char_limit)
