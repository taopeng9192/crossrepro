from __future__ import annotations

from pathlib import Path
import hashlib

from crossrepro.constants import INTERNAL_STATE_FILES


def checksums_from_snapshot(files: dict[str, bytes]) -> bytes:
    lines = [f"{hashlib.sha256(data).hexdigest()}  {name}" for name, data in sorted(files.items())]
    return ("\n".join(lines) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256sums(directory: Path) -> Path:
    output = directory / "SHA256SUMS"
    lines = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path == output or path.name in INTERNAL_STATE_FILES:
            continue
        relative = path.relative_to(directory)
        lines.append(f"{sha256_file(path)}  {relative.as_posix()}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
