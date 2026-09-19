from __future__ import annotations

from pathlib import Path, PureWindowsPath
import platform
import re
import shutil
import stat
import subprocess


def detect_current_platform() -> str:
    value = platform.system().lower()
    if value == "windows":
        return "windows"
    if value == "darwin":
        return "macos"
    return "linux"


def _is_windows_python_alias(path: str) -> bool:
    """Identify Python alias candidates; their size does not prove availability."""
    windows_path = PureWindowsPath(path)
    if (platform.system().lower() != "windows"
            or "windowsapps" not in (part.lower() for part in windows_path.parts)
            or not re.fullmatch(r"python(?:\d+(?:\.\d+)*)?\.exe", windows_path.name, re.IGNORECASE)):
        return False
    try:
        info = Path(path).lstat()
    except OSError:
        return False
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(info, "st_file_attributes", 0) & reparse_point and info.st_size == 0)


def command_exists(name: str) -> bool:
    path = shutil.which(name)
    if path is None:
        return False
    if _is_windows_python_alias(path):
        # App Installer's Python placeholder is discoverable but cannot run code.
        # Probe only Python aliases, without importing site or user startup code.
        try:
            result = subprocess.run(
                [path, "-I", "-S", "-c", "pass"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=5, check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0
    return True


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
