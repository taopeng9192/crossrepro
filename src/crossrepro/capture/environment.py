from __future__ import annotations

import locale
import os
import platform
import shutil
import subprocess

from crossrepro import __version__

SAFE_ENV_KEYS = ("LANG", "LC_ALL", "TERM", "CI", "SHELL", "COMSPEC")


def tool_version(executable: str, args: list[str]) -> str | None:
    resolved = shutil.which(executable)
    if not resolved:
        return None
    try:
        completed = subprocess.run(
            [resolved, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (completed.stdout or completed.stderr or "").strip()
    return output.splitlines()[0] if output else None


def collect_environment() -> dict:
    safe_env = {key: os.environ[key] for key in SAFE_ENV_KEYS if key in os.environ}
    try:
        language, encoding = locale.getlocale()
    except Exception:
        language, encoding = None, None
    return {
        "crossrepro_version": __version__,
        "os": platform.system().lower(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "node": tool_version("node", ["--version"]),
        "git": tool_version("git", ["--version"]),
        "shell_env": safe_env,
        "locale": {"language": language, "encoding": encoding},
    }
