import platform
import shutil
import subprocess


class ClipboardError(RuntimeError):
    """Raised when clipboard access fails."""


def _read_command() -> list[str]:
    system = platform.system()

    if system == "Linux":
        if shutil.which("wl-paste"):
            return ["wl-paste", "--no-newline"]
        if shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard", "-o"]
        if shutil.which("xsel"):
            return ["xsel", "--clipboard", "--output"]
        raise ClipboardError(
            "No supported clipboard reader found. "
            "Install wl-clipboard, xclip, or xsel."
        )

    if system == "Darwin":
        return ["pbpaste"]

    if system == "Windows":
        if not shutil.which("powershell"):
            raise ClipboardError("PowerShell is required to read the clipboard.")
        return [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "[Console]::OutputEncoding = "
                "[System.Text.UTF8Encoding]::new(); Get-Clipboard -Raw"
            ),
        ]

    raise ClipboardError(f"Unsupported operating system: {system}")


def _write_command() -> list[str]:
    system = platform.system()

    if system == "Linux":
        if shutil.which("wl-copy"):
            return ["wl-copy"]
        if shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard", "-i"]
        if shutil.which("xsel"):
            return ["xsel", "--clipboard", "--input"]
        raise ClipboardError(
            "No supported clipboard writer found. "
            "Install wl-clipboard, xclip, or xsel."
        )

    if system == "Darwin":
        return ["pbcopy"]

    if system == "Windows":
        if not shutil.which("clip"):
            raise ClipboardError("The Windows clip command was not found.")
        return ["clip"]

    raise ClipboardError(f"Unsupported operating system: {system}")


def read_clipboard() -> str:
    """Read text from the system clipboard."""
    command = _read_command()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            check=True,
        )
    except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
        raise ClipboardError(f"Could not read clipboard text: {exc}") from exc

    return result.stdout


def write_clipboard(text: str) -> None:
    """Replace the system clipboard contents with text."""
    command = _write_command()

    try:
        subprocess.run(
            command,
            input=text,
            text=True,
            encoding="utf-8",
            check=True,
            stdout=subprocess.DEVNULL,
        )
    except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
        raise ClipboardError(f"Could not write clipboard text: {exc}") from exc