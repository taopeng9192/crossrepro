from __future__ import annotations

from pathlib import Path
import json
import stat
import zipfile

from crossrepro.constants import INTERNAL_STATE_FILES
from crossrepro.redact.engine import contains_high_risk_secret, redact_text
from crossrepro.schema.loader import parse_repro
from crossrepro.schema.validator import validate_repro
from .hashing import checksums_from_snapshot
from .manifest import manifest_from_snapshot


class UnsafeBundleError(RuntimeError):
    pass


def _reject_link(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise UnsafeBundleError("links/reparse points cannot be packed")


def safety_scan(directory: Path) -> dict[str, bytes]:
    """Snapshot and scan the exact bytes that will enter the archive."""
    _reject_link(directory)
    files: dict[str, bytes] = {}
    for path in sorted(directory.rglob("*")):
        _reject_link(path)
        if path.is_dir():
            continue
        if not path.is_file():
            raise UnsafeBundleError("only regular text files can be packed")
        relative = path.relative_to(directory).as_posix()
        if relative in INTERNAL_STATE_FILES or relative in {"manifest.json", "SHA256SUMS"}:
            continue
        if any(part.lower().startswith("raw_") for part in path.relative_to(directory).parts):
            raise UnsafeBundleError("raw evidence file cannot be packed")
        if redact_text(relative).matches:
            raise UnsafeBundleError("sensitive data in a bundle filename; rename it before packing")
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnsafeBundleError("bundle content must be UTF-8 text so it can be scanned") from exc
        if "\x00" in text:
            raise UnsafeBundleError("binary content cannot be safely scanned")
        if contains_high_risk_secret(text):
            raise UnsafeBundleError("potential high-risk secret remains in bundle content")
        files[relative] = data
    return files


def build_bundle(source_dir: Path, output: Path) -> Path:
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(f"bundle source directory not found: {source_dir}")
    _reject_link(source_dir)
    source_dir = source_dir.resolve()
    if output.is_symlink():
        raise UnsafeBundleError("bundle output cannot be a link")
    output = output.resolve()
    try:
        output.relative_to(source_dir)
    except ValueError:
        pass
    else:
        raise ValueError("bundle output must be outside the source directory")
    if output.exists():
        raise FileExistsError("bundle output already exists; choose a new output path")
    files = safety_scan(source_dir)
    if "repro.yml" not in files:
        raise ValueError("bundle source must contain repro.yml")
    validate_repro(parse_repro(files["repro.yml"].decode("utf-8")))
    manifest = manifest_from_snapshot(files)
    files["manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    files["SHA256SUMS"] = checksums_from_snapshot(files)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        try:
            with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in sorted(files.items()):
                    archive.writestr(name, data)
        except BaseException:
            handle.close()
            output.unlink()
            raise
    return output
