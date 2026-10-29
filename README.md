# Segclip

Split long clipboard text into ordered, numbered segments for sequential submission to AI assistants.

## Features

- Lossless segmentation with natural-boundary preference.
- Configurable character limit and sequence markers.
- Interactive clipboard workflow: press Space to copy the next segment; quit with Q or Esc.
- Text within the character limit is copied unchanged, without added markers.

## Installation

Install from the repository using `uv`:

```bash
uv tool install .
```

This installs the `segclip` command so it can be run directly from any directory.

## Usage

```bash
segclip
```

Configure the character limit and markers in `segclip.toml`. Override the configured limit when needed:

```bash
segclip --char-limit 30000
```

## Development

```bash
uv run pytest
uv run ruff check .
```
