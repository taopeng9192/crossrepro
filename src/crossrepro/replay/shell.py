from __future__ import annotations

import platform
import shutil


def detect_current_platform() -> str:
    value = platform.system().lower()
    if value == "windows":
        return "windows"
    if value == "darwin":
        return "macos"
    return "linux"


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def resolve_shell(requested: str | None) -> str | None:
    if requested:
        return requested if shutil.which(requested) else None
    current = detect_current_platform()
    if current == "windows":
        for candidate in ("pwsh", "powershell", "cmd"):
            if shutil.which(candidate):
                return candidate
        return None
    for candidate in ("bash", "sh"):
        if shutil.which(candidate):
            return candidate
    return None
