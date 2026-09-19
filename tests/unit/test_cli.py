from pathlib import Path

from click.testing import CliRunner

from crossrepro.capture.runner import CommandResult
from crossrepro.cli import main


def fake_result(command: str, code=7):
    return CommandResult(
        command=command,
        shell="bash",
        exit_code=code,
        stdout="hello test@example.com\n",
        stderr="api_key=TEST_ONLY_SECRET_123456\n",
        started_at="a",
        finished_at="b",
        duration_ms=1,
        timed_out=False,
    )


def test_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for name in ("collect", "replay", "pack", "ci", "fix"):
        assert name in result.output


def test_collect_writes_sanitized_evidence(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.cli.run_command", lambda command, **kwargs: fake_result(command))
    monkeypatch.setattr("crossrepro.cli.collect_environment", lambda: {"os": "test"})
    monkeypatch.setattr("crossrepro.cli.collect_git_context", lambda cwd: None)
    out = tmp_path / "state"
    result = CliRunner().invoke(main, ["collect", "--command-text", "python app.py", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "repro.yml").exists()
    stdout = (out / "evidence" / "stdout.txt").read_text(encoding="utf-8")
    stderr = (out / "evidence" / "stderr.txt").read_text(encoding="utf-8")
    assert "test@example.com" not in stdout
    assert "TEST_ONLY_SECRET_123456" not in stderr


def test_collect_timeout_does_not_create_invalid_repro(monkeypatch, tmp_path: Path):
    timed = fake_result("x")
    timed.exit_code = None
    timed.timed_out = True
    monkeypatch.setattr("crossrepro.cli.run_command", lambda command, **kwargs: timed)
    monkeypatch.setattr("crossrepro.cli.collect_environment", lambda: {})
    monkeypatch.setattr("crossrepro.cli.collect_git_context", lambda cwd: None)
    out = tmp_path / "state"
    result = CliRunner().invoke(main, ["collect", "--command-text", "x", "--out", str(out)])
    assert result.exit_code != 0
    assert not (out / "repro.yml").exists()
    assert (out / "CAPTURE_NEEDS_MANUAL_REVIEW.txt").exists()


def test_collect_success_requires_manual_signature(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.cli.run_command", lambda command, **kwargs: fake_result(command, code=0))
    monkeypatch.setattr("crossrepro.cli.collect_environment", lambda: {})
    monkeypatch.setattr("crossrepro.cli.collect_git_context", lambda cwd: None)
    out = tmp_path / "state"
    result = CliRunner().invoke(main, ["collect", "--command-text", "python ok.py", "--out", str(out)])
    assert result.exit_code == 0
    assert not (out / "repro.yml").exists()
    assert (out / "CAPTURE_NEEDS_MANUAL_REVIEW.txt").exists()


def test_collect_refuses_non_crossrepro_existing_directory(monkeypatch, tmp_path: Path):
    out = tmp_path / "existing"
    out.mkdir()
    (out / "keep.txt").write_text("important", encoding="utf-8")
    result = CliRunner().invoke(main, ["collect", "--command-text", "x", "--out", str(out)])
    assert result.exit_code != 0
    assert (out / "keep.txt").read_text(encoding="utf-8") == "important"


def test_collect_command_secret_requires_manual_review(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.cli.run_command", lambda command, **kwargs: fake_result(command, code=2))
    monkeypatch.setattr("crossrepro.cli.collect_environment", lambda: {})
    monkeypatch.setattr("crossrepro.cli.collect_git_context", lambda cwd: None)
    out = tmp_path / "state"
    result = CliRunner().invoke(
        main,
        ["collect", "--command-text", "tool --api_key=TEST_ONLY_SECRET_123456", "--out", str(out)],
    )
    assert result.exit_code == 0
    assert not (out / "repro.yml").exists()
    assert "required redaction" in result.output


def test_collect_redacts_git_metadata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.cli.run_command", lambda command, **kwargs: fake_result(command))
    monkeypatch.setattr("crossrepro.cli.collect_environment", lambda: {"path": "/home/alice/project"})
    monkeypatch.setattr(
        "crossrepro.cli.collect_git_context",
        lambda cwd: {"changed_files": ["reports/test@example.com.txt"]},
    )
    out = tmp_path / "state"
    result = CliRunner().invoke(main, ["collect", "--command-text", "python app.py", "--out", str(out)])
    assert result.exit_code == 0
    env_text = (out / "evidence" / "environment.json").read_text(encoding="utf-8")
    git_text = (out / "evidence" / "git.json").read_text(encoding="utf-8")
    assert "alice" not in env_text
    assert "test@example.com" not in git_text


def test_invalid_repro_cli_is_human_readable(tmp_path: Path):
    path = tmp_path / "bad.yml"
    path.write_text("version: 1\nname: bad\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["replay", str(path)])
    assert result.exit_code != 0
    assert "Error:" in result.output
    assert "Traceback" not in result.output


def test_pack_command(monkeypatch, tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "x.zip"
    monkeypatch.setattr("crossrepro.cli.build_bundle", lambda source, output: output)
    result = CliRunner().invoke(main, ["pack", "--source", str(source), "--output", str(output)])
    assert result.exit_code == 0
    assert "Bundle:" in result.output


def test_ci_command(monkeypatch, tmp_path: Path):
    repro = tmp_path / "repro.yml"
    repro.write_text(
        "version: 1\nname: x\ncommand: {run: 'x'}\nbug_signature: {exit_code: {equals: 1}}\n",
        encoding="utf-8",
    )
    output = tmp_path / "workflow.yml"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("crossrepro.cli.generate_github_workflow", lambda spec, output, **kwargs: output)
    result = CliRunner().invoke(main, ["ci", str(repro), "--output", str(output)])
    assert result.exit_code == 0
    assert "Workflow:" in result.output
