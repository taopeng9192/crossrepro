import subprocess
from types import SimpleNamespace

import pytest

import crossrepro.replay.shell as mod


def test_detect_platform_branches(monkeypatch):
    monkeypatch.setattr(mod.platform, "system", lambda: "Windows")
    assert mod.detect_current_platform() == "windows"
    monkeypatch.setattr(mod.platform, "system", lambda: "Darwin")
    assert mod.detect_current_platform() == "macos"
    monkeypatch.setattr(mod.platform, "system", lambda: "Linux")
    assert mod.detect_current_platform() == "linux"


def test_command_exists(monkeypatch):
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/x" if name == "yes" else None)
    assert mod.command_exists("yes")
    assert not mod.command_exists("no")


@pytest.fixture
def windows_alias(monkeypatch):
    monkeypatch.setattr(mod.platform, "system", lambda: "Windows")
    monkeypatch.setattr(mod.shutil, "which", lambda name: r"C:\Users\Example\AppData\Local\Microsoft\WindowsApps\python.exe")
    monkeypatch.setattr(mod.Path, "lstat", lambda path: SimpleNamespace(st_file_attributes=0x400, st_size=0))


def test_command_exists_rejects_unavailable_windows_app_alias(monkeypatch, windows_alias):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=9009))
    assert not mod.command_exists("python")


def test_working_python_alias_is_allowed(monkeypatch, windows_alias):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    assert mod.command_exists("python")


def test_other_app_alias_is_not_rejected_or_executed(monkeypatch, windows_alias):
    monkeypatch.setattr(mod.shutil, "which", lambda name: r"C:\Users\Example\AppData\Local\Microsoft\WindowsApps\tool.exe")
    def unexpected_probe(*args, **kwargs):
        pytest.fail("must not execute arbitrary requirements during discovery")
    monkeypatch.setattr(subprocess, "run", unexpected_probe)
    assert mod.command_exists("tool")


@pytest.mark.parametrize("error", [OSError("cannot start"), subprocess.TimeoutExpired("python", 5)])
def test_python_alias_probe_failure_is_unavailable(monkeypatch, windows_alias, error):
    def failed_probe(*args, **kwargs):
        assert kwargs["timeout"] == 5
        raise error
    monkeypatch.setattr(subprocess, "run", failed_probe)
    assert not mod.command_exists("python")


def test_resolve_requested_shell(monkeypatch):
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/x" if name == "bash" else None)
    assert mod.resolve_shell("bash") == "bash"
    assert mod.resolve_shell("nope") is None


def test_resolve_windows_default(monkeypatch):
    monkeypatch.setattr(mod, "detect_current_platform", lambda: "windows")
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/x" if name == "powershell" else None)
    assert mod.resolve_shell(None) == "powershell"
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    assert mod.resolve_shell(None) is None


def test_resolve_posix_default_and_none(monkeypatch):
    monkeypatch.setattr(mod, "detect_current_platform", lambda: "linux")
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/x" if name == "sh" else None)
    assert mod.resolve_shell(None) == "sh"
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    assert mod.resolve_shell(None) is None
