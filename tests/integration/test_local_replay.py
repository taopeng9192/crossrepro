from pathlib import Path

from crossrepro.replay.runner import replay
from crossrepro.schema.loader import load_repro
from crossrepro.schema.validator import validate_repro
from crossrepro.verdict.evaluator import Verdict, evaluate

ROOT = Path(__file__).resolve().parents[2]


def test_secret_example_replays_locally():
    path = ROOT / "examples" / "secret-redaction" / "repro.yml"
    spec = load_repro(path)
    validate_repro(spec)
    execution = replay(spec, base_dir=ROOT, timeout=20)
    result = evaluate(execution, spec.bug_signature)
    assert result.verdict == Verdict.REPRODUCED
    assert "TEST_ONLY_SECRET_123456" not in execution.stdout
    assert "test@example.com" not in execution.stdout


def test_missing_runtime_is_blocked():
    path = ROOT / "examples" / "missing-runtime" / "repro.yml"
    spec = load_repro(path)
    validate_repro(spec)
    execution = replay(spec, base_dir=ROOT, timeout=20)
    result = evaluate(execution, spec.bug_signature)
    assert result.verdict == Verdict.ENVIRONMENT_BLOCKED


def test_shell_glob_example_has_expected_platform_difference():
    spec = load_repro(ROOT / "examples" / "shell-glob" / "repro.yml")
    validate_repro(spec)
    execution = replay(spec, base_dir=ROOT, timeout=20)
    expected = Verdict.REPRODUCED if execution.platform == "windows" else Verdict.NOT_REPRODUCED
    assert evaluate(execution, spec.bug_signature).verdict == expected
