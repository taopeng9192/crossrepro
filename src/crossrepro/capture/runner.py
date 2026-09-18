from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import platform
import base64
import locale
import os
import signal
import shutil
import subprocess
import time


_TIMEOUT_DRAIN_SECONDS = 3


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_shell() -> str:
    if platform.system().lower() == "windows":
        if shutil.which("pwsh"):
            return "pwsh"
        if shutil.which("powershell"):
            return "powershell"
        return "cmd"
    if shutil.which("bash"):
        return "bash"
    return "sh"


def shell_argv(shell: str, command: str) -> list[str]:
    normalized = shell.lower()
    if normalized in {"bash", "sh", "zsh"}:
        return [shell, "-lc", command]
    if normalized in {"pwsh", "powershell"}:
        # -Command otherwise maps native nonzero statuses to 1. EncodedCommand
        # also avoids Windows argv quoting changing quotes inside the script.
        script = (
            "$global:LASTEXITCODE = 0\n"
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)\n"
            "$OutputEncoding = [Console]::OutputEncoding\n"
            + command + "\n"
            "$crossreproSucceeded = $?\n"
            "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n"
            "if (-not $crossreproSucceeded) { exit 1 }\n"
            "exit 0\n"
        )
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        return [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]
    if normalized in {"cmd", "cmd.exe"}:
        return [shell, "/d", "/s", "/c", command]
    return [shell, "-c", command]


def decode_output(value: bytes | None) -> str:
    if not value:
        return ""
    for encoding in ("utf-8", locale.getpreferredencoding(False)):
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            pass
    return value.decode("utf-8", errors="replace")


def _stop_process_tree(process: subprocess.Popen) -> None:
    """Stop only the process tree started for this reproduction."""
    if os.name == "nt":
        try:
            subprocess.run(
                [str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"),
                 "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=_TIMEOUT_DRAIN_SECONDS,
            )
        except subprocess.TimeoutExpired:
            pass
        if process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _close_capture_streams(process: subprocess.Popen) -> None:
    """Release local pipe handles when a detached child keeps them open."""
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def _partial_bytes(value: bytes | None) -> bytes:
    return value or b""


@dataclass(slots=True)
class CommandResult:
    command: str
    shell: str
    exit_code: int | None
    stdout: str
    stderr: str
    started_at: str
    finished_at: str
    duration_ms: int
    timed_out: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def run_command(
    command: str,
    *,
    cwd: Path | None = None,
    shell: str | None = None,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> CommandResult:
    if timeout is not None and timeout <= 0:
        raise ValueError("timeout must be positive")
    selected_shell = shell or default_shell()
    started_at = utc_now()
    started_monotonic = time.monotonic()
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    process = subprocess.Popen(
        shell_argv(selected_shell, command),
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **options,
    )
    close_capture_streams = True
    try:
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
            exit_code = process.returncode
            timed_out = False
        except subprocess.TimeoutExpired as timeout_error:
            _stop_process_tree(process)
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=_TIMEOUT_DRAIN_SECONDS)
            except subprocess.TimeoutExpired as drain_error:
                # A detached descendant can outlive the command tree and keep an
                # inherited stdout/stderr pipe open. Do not let that defeat the
                # caller's timeout; preserve whatever output communicate exposed.
                # Closing a stream while communicate's Windows reader thread is
                # blocked on it can block too. Those daemon threads are allowed
                # to finish after the timed-out result is returned.
                close_capture_streams = False
                stdout_bytes = _partial_bytes(drain_error.stdout) or _partial_bytes(timeout_error.stdout)
                stderr_bytes = _partial_bytes(drain_error.stderr) or _partial_bytes(timeout_error.stderr)
            exit_code = None
            timed_out = True
    finally:
        if process.poll() is None:
            _stop_process_tree(process)
            try:
                process.wait(timeout=_TIMEOUT_DRAIN_SECONDS)
            except subprocess.TimeoutExpired:
                pass
        if close_capture_streams:
            _close_capture_streams(process)
    stdout = decode_output(stdout_bytes)
    stderr = decode_output(stderr_bytes)
    duration_ms = int((time.monotonic() - started_monotonic) * 1000)
    return CommandResult(
        command=command,
        shell=selected_shell,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        started_at=started_at,
        finished_at=utc_now(),
        duration_ms=duration_ms,
        timed_out=timed_out,
    )
