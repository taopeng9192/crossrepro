from pathlib import Path

import crossrepro.capture.git as gitmod


def test_non_repo_returns_none(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(gitmod, "run_git", lambda cwd, *args: (1, ""))
    assert gitmod.collect_git_context(tmp_path) is None


def test_git_context_parses_status(monkeypatch, tmp_path: Path):
    def fake(cwd, *args):
        key = tuple(args)
        values = {
            ("rev-parse", "--is-inside-work-tree"): (0, "true"),
            ("rev-parse", "--abbrev-ref", "HEAD"): (0, "main"),
            ("rev-parse", "HEAD"): (0, "abc123"),
            ("status", "--porcelain", "-z"): (0, " M src/a.py\0R  new.txt\0old.txt\0"),
        }
        return values[key]
    monkeypatch.setattr(gitmod, "run_git", fake)
    info = gitmod.collect_git_context(tmp_path)
    assert info == {
        "branch": "main",
        "commit": "abc123",
        "dirty": True,
        "changed_files": ["src/a.py", "new.txt"],
    }


def test_run_git_when_git_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(gitmod.shutil, "which", lambda name: None)
    assert gitmod.run_git(tmp_path, "status") == (127, "")


def test_run_git_handles_subprocess_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(gitmod.shutil, "which", lambda name: "/git")
    monkeypatch.setattr(gitmod.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("boom")))
    assert gitmod.run_git(tmp_path, "status") == (1, "")


def test_run_git_success(monkeypatch, tmp_path: Path):
    class Done:
        returncode = 0
        stdout = " main \n"
    monkeypatch.setattr(gitmod.shutil, "which", lambda name: "/git")
    monkeypatch.setattr(gitmod.subprocess, "run", lambda *a, **k: Done())
    assert gitmod.run_git(tmp_path, "branch") == (0, "main")


def test_porcelain_status_preserves_leading_spaces(monkeypatch, tmp_path):
    class Done:
        returncode = 0
        stdout = " M src/a.py\0??  leading space.txt\0"
    monkeypatch.setattr(gitmod.shutil, "which", lambda _: "/git")
    monkeypatch.setattr(gitmod.subprocess, "run", lambda *a, **k: Done())
    assert gitmod.run_git(tmp_path, "status", "--porcelain", "-z")[1] == Done.stdout
