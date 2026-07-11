"""Load the repository .env into os.environ at application startup.

Local Whisper needs two things in the process environment before any CUDA
code runs:

- WHISPER_MODEL_PATH (and friends), which can be set at any time, and
- LD_LIBRARY_PATH pointing at the pip-installed nvidia-cublas/nvidia-cudnn
  libraries, which the dynamic linker reads ONLY at process start.

Because LD_LIBRARY_PATH cannot take effect inside a running process, the
loader re-execs the interpreter once when .env adds new library paths. Under
systemd (EnvironmentFile=) the variables are already present, so no re-exec
happens.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REEXEC_SENTINEL = "MARKDOWN_CONVERTER_REEXEC"


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines; skip comments, blanks, and malformed lines."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def apply_env(values: dict[str, str], environ) -> bool:
    """Fill missing variables without overriding existing ones.

    LD_LIBRARY_PATH is merged: entries from .env that the current value does
    not already contain are prepended. Returns True when LD_LIBRARY_PATH
    changed, which requires a process re-exec to take effect.
    """
    needs_reexec = False
    for key, value in values.items():
        if not value:
            continue
        if key == "LD_LIBRARY_PATH":
            current = environ.get(key, "")
            current_entries = [entry for entry in current.split(":") if entry]
            missing = [
                entry
                for entry in value.split(":")
                if entry and entry not in current_entries
            ]
            if missing:
                environ[key] = ":".join(missing + current_entries)
                needs_reexec = True
        elif key not in environ:
            environ[key] = value
    return needs_reexec


def load_dotenv_and_reexec() -> None:
    """Load .env next to this file; re-exec once if LD_LIBRARY_PATH changed."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    needs_reexec = apply_env(parse_env_file(env_path), os.environ)
    if needs_reexec and _REEXEC_SENTINEL not in os.environ:
        os.environ[_REEXEC_SENTINEL] = "1"
        os.execv(sys.executable, [sys.executable, *sys.argv])
