from crossrepro.capture.environment import collect_environment


def test_environment_is_allowlist_first(monkeypatch):
    monkeypatch.setenv("VERY_SECRET_TOKEN", "do-not-collect")
    monkeypatch.setenv("LANG", "C.UTF-8")
    info = collect_environment()
    assert "VERY_SECRET_TOKEN" not in info["shell_env"]
    assert info["shell_env"].get("LANG") == "C.UTF-8"
    assert "python" in info
    assert "architecture" in info


def test_tool_version_missing(monkeypatch):
    import crossrepro.capture.environment as mod
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    assert mod.tool_version("missing", ["--version"]) is None


def test_tool_version_subprocess_error(monkeypatch):
    import crossrepro.capture.environment as mod
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/tool")
    def boom(*args, **kwargs):
        raise OSError("boom")
    monkeypatch.setattr(mod.subprocess, "run", boom)
    assert mod.tool_version("tool", ["--version"]) is None


def test_collect_environment_locale_failure(monkeypatch):
    import crossrepro.capture.environment as mod
    monkeypatch.setattr(mod.locale, "getlocale", lambda: (_ for _ in ()).throw(RuntimeError("bad locale")))
    monkeypatch.setattr(mod, "tool_version", lambda *args, **kwargs: None)
    info = mod.collect_environment()
    assert info["locale"] == {"language": None, "encoding": None}
