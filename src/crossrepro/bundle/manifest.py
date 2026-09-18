from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from crossrepro import __version__
from crossrepro.constants import INTERNAL_STATE_FILES


def manifest_from_snapshot(files: dict[str, bytes]) -> dict:
    return {
        "crossrepro_version": __version__,
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [{"path": name, "size": len(data)} for name, data in sorted(files.items())],
    }


def build_manifest(directory: Path) -> dict:
    files = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name in {"manifest.json", "SHA256SUMS"} or path.name in INTERNAL_STATE_FILES:
            continue
        files.append({
            "path": path.relative_to(directory).as_posix(),
            "size": path.stat().st_size,
        })
    return {
        "crossrepro_version": __version__,
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
