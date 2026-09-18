import sys
import base64
import shutil
import pytest
from pathlib import Path

from crossrepro.capture.runner import run_command, shell_argv, default_shell


def python_command(code):
    if default_shell() in {"pwsh", "powershell"}:
        executable = sys.executable.replace("'", "''")
        return f"& '{executable}' -c '{code}'"
    return f'"{sys.executable}" -c "{code}"'


def test_shell_argv_bash():
    assert shell_argv("bash", "echo hi") == ["bash", "-lc", "echo hi"]


def test_run_command_captures_stdout_and_exit_code(tmp_path: Path):
    command = python_command("print(123)")
    result = run_command(command, cwd=tmp_path, timeout=10)
    assert result.exit_code == 0
    assert result.stdout.strip() == "123"
    assert not result.timed_out
    assert result.duration_ms >= 0


def test_run_command_timeout(tmp_path: Path):
    command = python_command("import time; time.sleep(20)")
    result = run_command(command, cwd=tmp_path, timeout=1)
    assert result.exit_code is None
    assert result.timed_out


def test_default_shell_windows_preferences(monkeypatch):
    import crossrepro.capture.runner as mod
    monkeypatch.setattr(mod.platform, "system", lambda: "Windows")
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/x" if name == "pwsh" else None)
    assert mod.default_shell() == "pwsh"
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/x" if name == "powershell" else None)
    assert mod.default_shell() == "powershell"
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    assert mod.default_shell() == "cmd"


def test_default_shell_posix_fallback(monkeypatch):
    import crossrepro.capture.runner as mod
    monkeypatch.setattr(mod.platform, "system", lambda: "Linux")
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    assert mod.default_shell() == "sh"


def test_shell_argv_other_shells():
    argv = shell_argv("pwsh", "x")
    assert argv[-2] == "-EncodedCommand"
    assert "\nx\n" in base64.b64decode(argv[-1]).decode("utf-16le")
    assert shell_argv("cmd", "x") == ["cmd", "/d", "/s", "/c", "x"]
    assert shell_argv("custom", "x") == ["custom", "-c", "x"]


@pytest.mark.parametrize("shell", ["pwsh", "powershell"])
def test_powershell_preserves_native_exit_code_and_quoting(shell, tmp_path):
    if not shutil.which(shell):
        pytest.skip(f"{shell} is not available on this runner")
    executable = sys.executable.replace("'", "''")
    result = run_command(f"& '{executable}' -c 'import sys; print(123); sys.exit(7)'", shell=shell, cwd=tmp_path, timeout=15)
    assert result.exit_code == 7
    assert result.stdout.strip() == "123"


def test_non_utf8_output_does_not_crash_reader(tmp_path):
    result = run_command(python_command("import os; os.write(1, bytes([255, 254, 65]))"), cwd=tmp_path, timeout=15)
    assert result.exit_code == 0
    assert "A" in result.stdout
