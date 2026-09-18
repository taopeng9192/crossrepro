from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from crossrepro.constants import GITHUB_RUNNERS, SUPPORTED_SCHEMA_VERSION, SUPPORTED_SHELLS
from .models import ReproSpec


class InvalidReproSpec(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("Invalid repro.yml:\n- " + "\n- ".join(errors))


def _unsafe_relative_path(value: str) -> bool:
    if not value.strip():
        return True
    windows = PureWindowsPath(value)
    if PurePosixPath(value).is_absolute() or windows.drive or windows.root or ":" in value or "\x00" in value:
        return True
    parts = value.replace("\\", "/").split("/")
    return ".." in parts


def validate_repro(spec: ReproSpec) -> None:
    errors: list[str] = []
    if type(spec.version) is not int or spec.version != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"version must be {SUPPORTED_SCHEMA_VERSION}")
    if not spec.name.strip():
        errors.append("name must be non-empty")
    if _unsafe_relative_path(spec.workdir):
        errors.append("workdir must be a non-empty relative path without '..'")

    all_commands = [spec.default_command, *spec.platform_commands.values()]
    for command in all_commands:
        if command.shell is not None and command.shell.lower() not in SUPPORTED_SHELLS:
            errors.append(f"unsupported shell: {command.shell}")

    signature = spec.bug_signature
    has_signature = any([
        signature.exit_code is not None,
        bool(signature.stdout and signature.stdout.contains),
        bool(signature.stderr and signature.stderr.contains),
        bool(signature.files and (signature.files.exists or signature.files.missing)),
    ])
    if not has_signature:
        errors.append("bug_signature must not be empty")

    if signature.exit_code:
        exit_signature = signature.exit_code
        if exit_signature.equals is None and exit_signature.mode != "nonzero":
            errors.append("exit_code requires 'equals' or mode: nonzero")
        if exit_signature.equals is not None and (not isinstance(exit_signature.equals, int) or isinstance(exit_signature.equals, bool)):
            errors.append("exit_code.equals must be an integer")
        if exit_signature.mode is not None and exit_signature.mode != "nonzero":
            errors.append("exit_code.mode must be 'nonzero'")
        if exit_signature.equals is not None and exit_signature.mode is not None:
            errors.append("exit_code cannot define both 'equals' and 'mode'")

    if signature.files:
        for value in [*signature.files.exists, *signature.files.missing]:
            if _unsafe_relative_path(value):
                errors.append(f"file signature path must stay inside workdir: {value}")
    for stream in (signature.stdout, signature.stderr):
        if stream and any(value == "" for value in stream.contains):
            errors.append("stream contains must not include empty strings")

    for command in spec.setup_commands:
        if not command.strip():
            errors.append("setup.commands must not contain empty commands")
    for command in spec.required_commands:
        if not command.strip():
            errors.append("requirements.commands must not contain empty command names")

    unknown_runners = set(spec.platforms) - GITHUB_RUNNERS
    if unknown_runners:
        errors.append("unsupported GitHub runner(s): " + ", ".join(sorted(unknown_runners)))
    if len(set(spec.platforms)) != len(spec.platforms):
        errors.append("platforms must not contain duplicates")

    if errors:
        raise InvalidReproSpec(errors)
