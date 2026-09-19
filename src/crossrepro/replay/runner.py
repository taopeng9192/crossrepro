from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path

from crossrepro.capture.runner import run_command
from crossrepro.redact.engine import redact_text, redact_data
from crossrepro.schema.models import ReproSpec
from .shell import command_exists, detect_current_platform, resolve_shell


@dataclass(slots=True)
class ReplayExecution:
    platform: str
    shell: str | None
    command: str | None
    exit_code: int | None
    stdout: str
    stderr: str
    workdir: str
    blocked_reason: str | None = None
    timed_out: bool = False
    _raw_stdout: str | None = field(default=None, repr=False)
    _raw_stderr: str | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return redact_data({item.name: getattr(self, item.name) for item in fields(self) if not item.name.startswith("_")})


def blocked(platform_key: str, workdir: Path, reason: str) -> ReplayExecution:
    return ReplayExecution(
        platform=platform_key,
        shell=None,
        command=None,
        exit_code=None,
        stdout="",
        stderr="",
        workdir=str(workdir),
        blocked_reason=redact_text(reason).text,
    )


def resolve_workdir(base_dir: Path, configured: str) -> Path:
    candidate = (base_dir / configured).resolve()
    base = base_dir.resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError("workdir escapes the replay base directory") from exc
    return candidate


def replay(spec: ReproSpec, *, base_dir: Path, timeout: int = 120) -> ReplayExecution:
    platform_key = detect_current_platform()
    try:
        workdir = resolve_workdir(base_dir, spec.workdir)
    except ValueError as exc:
        return blocked(platform_key, base_dir.resolve(), str(exc))
    if not workdir.exists() or not workdir.is_dir():
        return blocked(platform_key, workdir, f"workdir does not exist: {spec.workdir}")

    for required in spec.required_commands:
        if not command_exists(required):
            return blocked(platform_key, workdir, f"required command is not runnable: {required}")

    command_spec = spec.command_for(platform_key)
    shell = resolve_shell(command_spec.shell)
    if shell is None:
        return blocked(platform_key, workdir, f"shell not available: {command_spec.shell or '<default>'}")

    for setup_command in spec.setup_commands:
        try:
            result = run_command(setup_command, cwd=workdir, shell=shell, timeout=timeout)
        except OSError as exc:
            return blocked(platform_key, workdir, f"setup could not start: {exc}")
        safe_stderr = redact_text(result.stderr).text
        if result.timed_out:
            return blocked(platform_key, workdir, f"setup timed out: {setup_command}")
        if result.exit_code != 0:
            return blocked(platform_key, workdir, f"setup failed: {setup_command}; stderr={safe_stderr[:500]}")

    try:
        result = run_command(command_spec.run, cwd=workdir, shell=shell, timeout=timeout)
    except OSError as exc:
        return blocked(platform_key, workdir, f"target command could not start: {exc}")
    stdout = redact_text(result.stdout).text
    stderr = redact_text(result.stderr).text
    if result.timed_out:
        return ReplayExecution(
            platform=platform_key,
            shell=shell,
            command=redact_text(command_spec.run).text,
            exit_code=None,
            stdout=stdout,
            stderr=stderr,
            workdir=str(workdir),
            blocked_reason="target command timed out",
            timed_out=True,
        )
    return ReplayExecution(
        platform=platform_key,
        shell=shell,
        command=redact_text(command_spec.run).text,
        exit_code=result.exit_code,
        stdout=stdout,
        stderr=stderr,
        workdir=str(workdir),
        _raw_stdout=result.stdout,
        _raw_stderr=result.stderr,
    )
