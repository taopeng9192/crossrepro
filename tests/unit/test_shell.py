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
