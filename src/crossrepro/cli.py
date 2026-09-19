from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import shlex
import subprocess
import stat

import click
import yaml

from crossrepro.bundle.builder import UnsafeBundleError, build_bundle
from crossrepro.capture.environment import collect_environment
from crossrepro.capture.git import collect_git_context
from crossrepro.capture.runner import run_command, default_shell
from crossrepro.ci.github import generate_github_workflow
from crossrepro.constants import DEFAULT_LATEST_DIR, SUPPORTED_SHELLS
from crossrepro.redact.engine import redact_text, redact_data, redact_json
from crossrepro.repair.models import FixStatus
from crossrepro.repair.providers import CodexCliRepairProvider, FilePatchProvider, OpenAIRepairProvider
from crossrepro.repair.runner import fix as run_fix
from crossrepro.replay.runner import replay as run_replay
from crossrepro.schema.loader import ReproLoadError, load_repro
from crossrepro.schema.validator import InvalidReproSpec, validate_repro
from crossrepro.verdict.evaluator import evaluate


def command_from_parts(parts: tuple[str, ...], shell: str | None = None) -> str:
    selected = (shell or default_shell()).lower()
    if selected in {"pwsh", "powershell"}:
        return "& " + " ".join("'" + part.replace("'", "''") + "'" for part in parts)
    if selected in {"cmd", "cmd.exe"}:
        if any(any(char in part for char in '&|<>^%!\r\n') for part in parts):
            raise click.ClickException("cmd argument mode cannot preserve shell metacharacters; use --command-text")
        return subprocess.list2cmdline(list(parts))
    return shlex.join(parts)


def _load_validated(path: Path):
    try:
        spec = load_repro(path)
        validate_repro(spec)
        return spec
    except (ReproLoadError, InvalidReproSpec) as exc:
        raise click.ClickException(redact_text(str(exc)).text) from exc


STATE_MARKER = ".crossrepro-state"


def _reset_state_dir(out: Path) -> None:
    resolved = out.resolve()
    if Path.cwd().resolve().is_relative_to(resolved):
        raise click.ClickException("refusing to use the current working directory or its ancestor as capture output")
    for path in (out.absolute(), *out.absolute().parents):
        if path.exists() or path.is_symlink():
            info = path.lstat()
            if path.is_symlink() or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise click.ClickException("capture output cannot use links/reparse points")
    if out.exists():
        if not out.is_dir():
            raise click.ClickException(f"capture output exists and is not a directory: {out}")
        marker = out / STATE_MARKER
        try:
            valid_marker = marker.is_file() and marker.read_text(encoding="utf-8") == "crossrepro-state-v1\n"
        except UnicodeError:
            valid_marker = False
        if any(out.iterdir()) and not valid_marker:
            raise click.ClickException(
                f"refusing to delete non-CrossRepro directory: {out}; choose an empty directory or a prior CrossRepro state directory"
            )
        if marker.exists():
            permitted = {STATE_MARKER, "command.json", "repro.yml", "CAPTURE_NEEDS_MANUAL_REVIEW.txt", "manifest.json", "SHA256SUMS"}
            evidence_names = {"stdout.txt", "stderr.txt", "environment.json", "git.json", "redaction-report.json"}
            existing = list(out.rglob("*"))
            for path in existing:
                relative = path.relative_to(out).as_posix()
                info = path.lstat()
                linked = path.is_symlink() or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                allowed = (relative == "evidence" and path.is_dir()) or (path.is_file() and (relative in permitted or relative in {"evidence/" + name for name in evidence_names}))
                if linked or not allowed:
                    raise click.ClickException("capture output contains unrecognized files; choose a new empty directory")
            for path in existing:
                if path.is_file():
                    path.unlink()
    out.mkdir(parents=True, exist_ok=True)
    (out / STATE_MARKER).write_text("crossrepro-state-v1\n", encoding="utf-8")


def _write_manual_review(out: Path, reason: str) -> None:
    (out / "CAPTURE_NEEDS_MANUAL_REVIEW.txt").write_text(
        reason.rstrip() + "\nReview sanitized evidence and author/edit repro.yml manually.\n",
        encoding="utf-8",
    )


@click.group()
def main() -> None:
    """Cross-platform bug reproduction."""


@main.command(context_settings={"ignore_unknown_options": True})
@click.option(
    "--command-text",
    default=None,
    help="Exact command string. Recommended when shell quoting/globbing matters.",
)
@click.option("--shell", type=click.Choice(sorted(SUPPORTED_SHELLS)), default=None)
@click.option("--timeout", type=click.IntRange(min=1), default=120, show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=DEFAULT_LATEST_DIR, show_default=True)
@click.argument("command_parts", nargs=-1, type=click.UNPROCESSED)
def collect(command_text: str | None, shell: str | None, timeout: int, out: Path, command_parts: tuple[str, ...]) -> None:
    """Capture a command and write sanitized evidence plus a repro.yml draft."""
    if command_text:
        command = command_text
    elif command_parts:
        command = command_from_parts(command_parts, shell)
    else:
        raise click.ClickException("provide --command-text or a command after --")

    try:
        _reset_state_dir(out)
        result = run_command(command, cwd=Path.cwd(), shell=shell, timeout=timeout)
    except OSError as exc:
        raise click.ClickException(redact_text(f"capture could not start: {exc}").text) from exc
    command_redaction = redact_text(result.command)
    stdout_redaction = redact_text(result.stdout)
    stderr_redaction = redact_text(result.stderr)

    evidence = out / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "stdout.txt").write_text(stdout_redaction.text, encoding="utf-8")
    (evidence / "stderr.txt").write_text(stderr_redaction.text, encoding="utf-8")
    environment_redaction = redact_json(collect_environment())
    git_redaction = redact_json(collect_git_context(Path.cwd()))
    (evidence / "environment.json").write_text(environment_redaction.text, encoding="utf-8")
    (evidence / "git.json").write_text(git_redaction.text, encoding="utf-8")
    (evidence / "redaction-report.json").write_text(
        json.dumps(
            {
                "command": command_redaction.to_report(),
                "stdout": stdout_redaction.to_report(),
                "stderr": stderr_redaction.to_report(),
                "environment": environment_redaction.to_report(),
                "git": git_redaction.to_report(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    metadata = result.to_dict()
    metadata["command"] = command_redaction.text
    metadata["stdout"] = None
    metadata["stderr"] = None
    (out / "command.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    if result.timed_out or result.exit_code is None:
        _write_manual_review(out, "The command timed out, so no deterministic automatic bug signature was created.")
        raise click.ClickException(f"command timed out; evidence saved to {out}, but repro.yml was not generated")
    if result.exit_code == 0:
        _write_manual_review(out, "The command exited successfully (0). CrossRepro cannot infer a bug signature from exit status alone.")
        click.echo(f"Captured to {out}")
        click.echo("Exit code: 0")
        click.echo("No repro.yml generated: define the observable bug signature manually.")
        return
    if command_redaction.matches:
        _write_manual_review(
            out,
            "The command itself contained data that required redaction. A sanitized command may not be replayable; parameterize the sensitive value before creating repro.yml.",
        )
        click.echo(f"Captured to {out}")
        click.echo(f"Exit code: {result.exit_code}")
        click.echo("No repro.yml generated because the command required redaction.")
        return

    repro = {
        "version": 1,
        "name": "captured-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
        "workdir": ".",
        "command": {"default": {"shell": result.shell, "run": command_redaction.text}},
        "bug_signature": {"exit_code": {"equals": result.exit_code}},
        "platforms": ["windows-latest", "ubuntu-latest", "macos-latest"],
        "capture": {"stdout": True, "stderr": True, "environment": True, "git": True},
        "redaction": {"enabled": True},
    }
    (out / "repro.yml").write_text(yaml.safe_dump(repro, sort_keys=False), encoding="utf-8")
    click.echo(f"Captured to {out}")
    click.echo(f"Exit code: {result.exit_code}")
    if not command_text and command_parts:
        click.echo("Note: argument mode normalizes quoting. Use --command-text for shell/glob reproduction.")


@main.command()
@click.argument("repro_file", type=click.Path(path_type=Path, exists=True))
@click.option("--base-dir", type=click.Path(path_type=Path, exists=True, file_okay=False), default=Path("."), show_default=True)
@click.option("--report", type=click.Path(path_type=Path), default=Path("report.json"), show_default=True)
@click.option("--timeout", type=click.IntRange(min=1), default=120, show_default=True)
def replay(repro_file: Path, base_dir: Path, report: Path, timeout: int) -> None:
    """Replay a reproduction and write a deterministic report."""
    spec = _load_validated(repro_file)
    execution = run_replay(spec, base_dir=base_dir, timeout=timeout)
    verdict = evaluate(execution, spec.bug_signature)
    payload = {
        "schema_version": 1,
        "repro": spec.name,
        "execution": execution.to_dict(),
        "result": verdict.to_dict(),
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(redact_data(payload), indent=2), encoding="utf-8")
    click.echo(f"{execution.platform}: {verdict.verdict.value}")
    if verdict.blocked_reason:
        click.echo(f"Blocked: {verdict.blocked_reason}")


@main.command()
@click.option("--source", type=click.Path(path_type=Path, exists=True, file_okay=False), default=DEFAULT_LATEST_DIR, show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=None)
def pack(source: Path, output: Path | None) -> None:
    """Create a portable sanitized reproduction bundle."""
    if output is None:
        output = source.parent / f"{source.name}.crossrepro.zip"
    try:
        built = build_bundle(source, output)
    except (UnsafeBundleError, OSError, ValueError) as exc:
        raise click.ClickException(redact_text(str(exc)).text) from exc
    click.echo(f"Bundle: {built}")


@main.command()
@click.argument("repro_file", type=click.Path(path_type=Path, exists=True))
@click.option("--output", type=click.Path(path_type=Path), default=Path(".github/workflows/crossrepro.yml"), show_default=True)
@click.option("--install-source", default=".", show_default=True, help="CrossRepro source directory, wheel path, or published package requirement available to CI.")
def ci(repro_file: Path, output: Path, install_source: str) -> None:
    """Generate a GitHub Actions replay workflow."""
    spec = _load_validated(repro_file)
    try:
        relative = repro_file.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError as exc:
        raise click.ClickException("CI repro file must be inside the current repository directory") from exc
    if not install_source.strip() or install_source.startswith("-"):
        raise click.ClickException("provide a non-empty installation source, not a pip option")
    try:
        generated = generate_github_workflow(spec, output, repro_path=relative, install_source=install_source)
    except (ValueError, OSError) as exc:
        raise click.ClickException(redact_text(str(exc)).text) from exc
    click.echo(f"Workflow: {generated}")


@main.command()
@click.option("--repo", type=click.Path(path_type=Path, exists=True, file_okay=False), default=Path("."), show_default=True, help="Target project to repair.")
@click.option("--test", "test_command", required=True, help="Command that currently fails and should pass after the repair.")
@click.option("--provider", "provider_name", type=click.Choice(["codex", "openai"]), default="codex", show_default=True, help="Agent that proposes the patch.")
@click.option("--model", default=None, help="Optional model override for the selected provider. Required for provider=openai.")
@click.option("--patch-file", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=None, help="Previously reviewed unified diff to validate and optionally apply without calling an API.")
@click.option("--include", "includes", multiple=True, type=click.Path(path_type=str), help="Source file to send to the provider. Repeat to choose context explicitly.")
@click.option("--apply", is_flag=True, help="Apply the candidate to the target project only while verification runs. Failed verification is reverted.")
@click.option("--timeout", type=click.IntRange(min=1), default=120, show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=Path(".crossrepro/fix"), show_default=True, help="Directory for candidate.patch and fix-report.json.")
def fix(repo: Path, test_command: str, provider_name: str, model: str | None, patch_file: Path | None, includes: tuple[str, ...], apply: bool, timeout: int, out: Path) -> None:
    """Propose and test a repair for a failing command.

    The OpenAI provider receives selected text source and the sanitized failed-test
    output. A provider can only return a unified diff; CrossRepro validates and
    applies that diff itself. Use --apply to retain a verified repair.
    """
    root = repo.resolve()
    output = out if out.is_absolute() else root / out
    if patch_file:
        provider = FilePatchProvider(patch_file)
    elif provider_name == "codex":
        provider = CodexCliRepairProvider(repo=root, timeout=timeout, model=model)
    elif model:
        provider = OpenAIRepairProvider(model=model)
    else:
        raise click.ClickException("provider=openai requires --model; use provider=codex or --patch-file without an API key")
    result = run_fix(
        repo=root,
        test_command=test_command,
        provider=provider,
        patch_path=output / "candidate.patch",
        report_path=output / "fix-report.json",
        apply=apply,
        timeout=timeout,
        includes=includes,
    )
    click.echo(f"{result.status.value}: {result.summary}")
    if result.patch_path:
        click.echo(f"Patch: {result.patch_path}")
    if result.changed_files:
        click.echo("Changed files: " + ", ".join(result.changed_files))
    if result.detail:
        click.echo("Detail: " + result.detail)
    if result.status is not FixStatus.FIXED:
        raise click.exceptions.Exit(2)


if __name__ == "__main__":
    main()
