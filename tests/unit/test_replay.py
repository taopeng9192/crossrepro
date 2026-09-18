from pathlib import Path

from crossrepro.capture.runner import CommandResult
from crossrepro.replay.runner import replay
from crossrepro.schema.models import BugSignature, CommandSpec, ExitCodeSignature, ReproSpec


def spec(**kwargs):
    values = dict(
        version=1,
        name="x",
        workdir=".",
        setup_commands=[],
        default_command=CommandSpec(run="target", shell="bash"),
        platform_commands={},
        bug_signature=BugSignature(exit_code=ExitCodeSignature(equals=1)),
        required_commands=[],
        platforms=[],
    )
    values.update(kwargs)
    return ReproSpec(**values)


def result(command, code=0, stderr=""):
    return CommandResult(
        command=command,
        shell="bash",
        exit_code=code,
        stdout="",
        stderr=stderr,
        started_at="a",
        finished_at="b",
        duration_ms=1,
        timed_out=False,
    )


def test_missing_requirement_is_blocked(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.replay.runner.command_exists", lambda name: False)
    execution = replay(spec(required_commands=["missing"]), base_dir=tmp_path)
    assert "required command not found" in execution.blocked_reason


def test_setup_failure_is_blocked_and_redacted(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda value: "bash")
    monkeypatch.setattr("crossrepro.replay.runner.command_exists", lambda name: True)
    monkeypatch.setattr(
        "crossrepro.replay.runner.run_command",
        lambda command, **kwargs: result(command, code=2, stderr="password=TEST_ONLY_SECRET_123456"),
    )
    execution = replay(spec(setup_commands=["setup"]), base_dir=tmp_path)
    assert "setup failed" in execution.blocked_reason
    assert "TEST_ONLY_SECRET_123456" not in execution.blocked_reason


def test_target_executes_and_output_is_redacted(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda value: "bash")
    monkeypatch.setattr("crossrepro.replay.runner.command_exists", lambda name: True)
    monkeypatch.setattr(
        "crossrepro.replay.runner.run_command",
        lambda command, **kwargs: result(command, code=1, stderr="Bearer abcdefghijklmnop"),
    )
    execution = replay(spec(), base_dir=tmp_path)
    assert execution.exit_code == 1
    assert "abcdefghijklmnop" not in execution.stderr
    assert not execution.blocked_reason


def test_missing_workdir_is_blocked(tmp_path: Path):
    execution = replay(spec(workdir="missing"), base_dir=tmp_path)
    assert "workdir does not exist" in execution.blocked_reason


def test_missing_shell_is_blocked(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda value: None)
    execution = replay(spec(), base_dir=tmp_path)
    assert "shell not available" in execution.blocked_reason


def test_setup_timeout_is_blocked(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda value: "bash")
    monkeypatch.setattr("crossrepro.replay.runner.command_exists", lambda name: True)
    timed = result("setup")
    timed.exit_code = None
    timed.timed_out = True
    monkeypatch.setattr("crossrepro.replay.runner.run_command", lambda command, **kwargs: timed)
    execution = replay(spec(setup_commands=["setup"]), base_dir=tmp_path)
    assert "setup timed out" in execution.blocked_reason


def test_target_timeout_is_blocked(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda value: "bash")
    timed = result("target")
    timed.exit_code = None
    timed.timed_out = True
    monkeypatch.setattr("crossrepro.replay.runner.run_command", lambda command, **kwargs: timed)
    execution = replay(spec(), base_dir=tmp_path)
    assert execution.timed_out
    assert execution.blocked_reason == "target command timed out"


def test_platform_specific_command_is_selected(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("crossrepro.replay.runner.detect_current_platform", lambda: "windows")
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda value: "bash")
    seen = {}
    def fake_run(command, **kwargs):
        seen["command"] = command
        return result(command, code=1)
    monkeypatch.setattr("crossrepro.replay.runner.run_command", fake_run)
    custom = spec(platform_commands={"windows": CommandSpec(run="windows-target", shell="bash")})
    execution = replay(custom, base_dir=tmp_path)
    assert seen["command"] == "windows-target"
    assert execution.command == "windows-target"
