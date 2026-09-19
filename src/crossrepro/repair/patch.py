from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import time


class PatchError(ValueError):
    pass


@dataclass(slots=True)
class FilePatch:
    path: str
    hunks: list[tuple[int, list[str]]]


@dataclass(slots=True)
class FileSnapshot:
    text: str
    atime_ns: int
    mtime_ns: int


_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _path_from_header(value: str) -> str:
    raw = value.split("\t", 1)[0].strip()
    if raw == "/dev/null":
        raise PatchError("file creation and deletion are not supported")
    if raw.startswith(("a/", "b/")):
        raw = raw[2:]
    candidate = Path(raw)
    if not raw or candidate.is_absolute() or "\\" in raw or ".." in candidate.parts:
        raise PatchError("patch path must be a relative path inside the repository")
    return candidate.as_posix()


def parse_unified_diff(patch: str) -> list[FilePatch]:
    lines = patch.splitlines()
    files: list[FilePatch] = []
    index = 0
    seen: set[str] = set()
    while index < len(lines):
        if not lines[index].startswith("--- "):
            raise PatchError("each file patch must start with a --- header")
        old_path = _path_from_header(lines[index][4:])
        index += 1
        if index >= len(lines) or not lines[index].startswith("+++ "):
            raise PatchError("missing +++ header")
        new_path = _path_from_header(lines[index][4:])
        if old_path != new_path:
            raise PatchError("renames are not supported")
        if new_path in seen:
            raise PatchError("a file may appear only once in a patch")
        seen.add(new_path)
        index += 1
        hunks: list[tuple[int, list[str]]] = []
        while index < len(lines) and not lines[index].startswith("--- "):
            match = _HUNK.match(lines[index])
            if not match:
                raise PatchError("invalid unified-diff hunk header")
            start = int(match.group(1))
            index += 1
            body: list[str] = []
            while index < len(lines) and not lines[index].startswith(("@@ ", "--- ")):
                line = lines[index]
                if line == "\\ No newline at end of file":
                    index += 1
                    continue
                if not line or line[0] not in " +-":
                    raise PatchError("invalid unified-diff hunk line")
                body.append(line)
                index += 1
            hunks.append((start, body))
        if not hunks:
            raise PatchError("a file patch must contain at least one hunk")
        files.append(FilePatch(path=new_path, hunks=hunks))
    if not files:
        raise PatchError("patch is empty")
    return files


def _apply_to_text(original: str, file_patch: FilePatch) -> str:
    original_lines = original.splitlines()
    output: list[str] = []
    cursor = 0
    for start, hunk in file_patch.hunks:
        expected = start - 1
        if expected < cursor or expected > len(original_lines):
            raise PatchError(f"hunk positions do not apply to {file_patch.path}")
        output.extend(original_lines[cursor:expected])
        cursor = expected
        for line in hunk:
            marker, value = line[0], line[1:]
            if marker == "+":
                output.append(value)
                continue
            if cursor >= len(original_lines) or original_lines[cursor] != value:
                raise PatchError(f"hunk context does not apply to {file_patch.path}")
            if marker == " ":
                output.append(value)
            cursor += 1
    output.extend(original_lines[cursor:])
    suffix = "\n" if original.endswith("\n") or output else ""
    return "\n".join(output) + suffix


def stage_patch(
    repo: Path,
    patch: str,
    *,
    allowed_paths: set[str] | None = None,
) -> tuple[dict[Path, FileSnapshot], dict[Path, str]]:
    files = parse_unified_diff(patch)
    original: dict[Path, FileSnapshot] = {}
    updated: dict[Path, str] = {}
    root = repo.resolve()
    for item in files:
        if allowed_paths is not None and item.path not in allowed_paths:
            raise PatchError(f"patch target was not supplied to the provider: {item.path}")
        target = (root / item.path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise PatchError("patch escapes the repository") from exc
        if not target.is_file() or target.is_symlink():
            raise PatchError(f"patch target must be an existing regular file: {item.path}")
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise PatchError(f"patch target is not UTF-8 text: {item.path}") from exc
        metadata = target.stat()
        original[target] = FileSnapshot(text=text, atime_ns=metadata.st_atime_ns, mtime_ns=metadata.st_mtime_ns)
        updated[target] = _apply_to_text(text, item)
    return original, updated


def write_staged_patch(original: dict[Path, FileSnapshot], updated: dict[Path, str]) -> None:
    for target, new_text in updated.items():
        if target.read_text(encoding="utf-8") != original[target].text:
            raise PatchError(f"refusing to overwrite concurrently changed file: {target}")
    for target, new_text in updated.items():
        target.write_text(new_text, encoding="utf-8", newline="\n")
        snapshot = original[target]
        os.utime(target, ns=(snapshot.atime_ns, max(time.time_ns(), snapshot.mtime_ns + 1_000_000_000)))


def restore_staged_patch(original: dict[Path, FileSnapshot], updated: dict[Path, str]) -> None:
    for target, new_text in updated.items():
        if target.exists() and target.read_text(encoding="utf-8") == new_text:
            snapshot = original[target]
            target.write_text(snapshot.text, encoding="utf-8", newline="\n")
            os.utime(target, ns=(snapshot.atime_ns, snapshot.mtime_ns))
