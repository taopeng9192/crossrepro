from pathlib import Path

DEFAULT_STATE_DIR = Path(".crossrepro")
DEFAULT_LATEST_DIR = DEFAULT_STATE_DIR / "latest"
SUPPORTED_SCHEMA_VERSION = 1

PLATFORM_KEYS = {"windows", "linux", "macos"}
GITHUB_RUNNERS = {"windows-latest", "ubuntu-latest", "macos-latest"}
SUPPORTED_SHELLS = {"bash", "sh", "zsh", "pwsh", "powershell", "cmd", "cmd.exe"}

INTERNAL_STATE_FILES = {".crossrepro-state"}
