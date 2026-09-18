from pathlib import Path

from crossrepro.replay.runner import ReplayExecution
from crossrepro.schema.models import BugSignature, ExitCodeSignature, FileSignature, StreamSignature
from crossrepro.verdict.evaluator import Verdict, evaluate


def execution(tmp_path: Path, *, code=2, stdout="", stderr="os error 123", blocked=None):
    return ReplayExecution(
        platform="windows",
        shell="pwsh",
        command="example",
        exit_code=code,
        stdout=stdout,
        stderr=stderr,
        workdir=str(tmp_path),
        blocked_reason=blocked,
    )


def test_reproduced_when_all_checks_match(tmp_path: Path):
    signature = BugSignature(
        exit_code=ExitCodeSignature(equals=2),
        stderr=StreamSignature(contains=["os error 123"]),
    )
    result = evaluate(execution(tmp_path), signature)
    assert result.verdict == Verdict.REPRODUCED
    assert all(result.checks.values())


def test_not_reproduced_when_one_check_fails(tmp_path: Path):
    signature = BugSignature(
        exit_code=ExitCodeSignature(equals=2),
        stderr=StreamSignature(contains=["different"]),
    )
    assert evaluate(execution(tmp_path), signature).verdict == Verdict.NOT_REPRODUCED


def test_environment_blocked_short_circuits(tmp_path: Path):
    signature = BugSignature(exit_code=ExitCodeSignature(equals=2))
    result = evaluate(execution(tmp_path, blocked="missing tool"), signature)
    assert result.verdict == Verdict.ENVIRONMENT_BLOCKED
    assert result.checks == {}


def test_file_signatures(tmp_path: Path):
    (tmp_path / "exists.txt").write_text("x", encoding="utf-8")
    signature = BugSignature(files=FileSignature(exists=["exists.txt"], missing=["missing.txt"]))
    assert evaluate(execution(tmp_path, code=0, stderr=""), signature).verdict == Verdict.REPRODUCED


def test_nonzero_stdout_and_stderr_checks(tmp_path: Path):
    signature = BugSignature(
        exit_code=ExitCodeSignature(mode="nonzero"),
        stdout=StreamSignature(contains=["hello"]),
        stderr=StreamSignature(contains=["warn"]),
    )
    result = evaluate(execution(tmp_path, code=9, stdout="hello world", stderr="warn here"), signature)
    assert result.verdict == Verdict.REPRODUCED
    assert len(result.checks) == 3
