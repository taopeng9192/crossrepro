from pathlib import Path
import yaml

from crossrepro.ci.github import generate_github_workflow
from crossrepro.schema.models import BugSignature, CommandSpec, ExitCodeSignature, ReproSpec


def test_generated_workflow_has_three_platforms(tmp_path: Path):
    spec = ReproSpec(
        version=1,
        name="x",
        workdir=".",
        setup_commands=[],
        default_command=CommandSpec(run="python x.py"),
        platform_commands={},
        bug_signature=BugSignature(exit_code=ExitCodeSignature(equals=1)),
        required_commands=[],
        platforms=["windows-latest", "ubuntu-latest", "macos-latest"],
    )
    out = tmp_path / "workflow.yml"
    generate_github_workflow(spec, out, repro_path="examples/x/repro.yml")
    text = out.read_text(encoding="utf-8")
    loaded = yaml.safe_load(text)
    assert "on" in loaded
    jobs = loaded["jobs"]
    assert jobs["replay"]["strategy"]["matrix"]["os"] == spec.platforms
    replay = next(step for step in jobs["replay"]["steps"] if step["name"] == "Replay")
    assert replay["env"]["CROSSREPRO_SPEC"] == "examples/x/repro.yml"
    assert "if: always()" in text


def test_workflow_treats_paths_as_data(tmp_path):
    spec = ReproSpec(1, "x", ".", [], CommandSpec("echo ok"), {}, BugSignature(exit_code=ExitCodeSignature(equals=1)), [], [])
    path = 'examples/quote"; Write-Output injected/repro.yml'
    out = generate_github_workflow(spec, tmp_path / "workflow.yml", repro_path=path, install_source="dist/a wheel.whl")
    steps = yaml.safe_load(out.read_text(encoding="utf-8"))["jobs"]["replay"]["steps"]
    assert next(s for s in steps if s["name"] == "Replay")["env"]["CROSSREPRO_SPEC"] == path
    assert all("injected" not in s.get("run", "") for s in steps)
    assert next(s for s in steps if s["name"] == "Upload report")["with"]["if-no-files-found"] == "error"


def test_summary_marks_blocked_without_echoing_secrets(tmp_path):
    import json
    from crossrepro.ci.summary import write_summary
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"execution": {"platform": "windows", "shell": None, "command": "DO_NOT_RENDER"}, "result": {"verdict": "ENVIRONMENT_BLOCKED"}}), encoding="utf-8")
    out = tmp_path / "summary.md"
    write_summary(report, out)
    text = out.read_text(encoding="utf-8")
    assert "ENVIRONMENT_BLOCKED" in text
    assert "DO_NOT_RENDER" not in text


def test_workflow_rejects_expression_interpolation(tmp_path):
    import pytest
    spec = ReproSpec(1, "x", ".", [], CommandSpec("echo ok"), {}, BugSignature(exit_code=ExitCodeSignature(equals=1)), [], [])
    with pytest.raises(ValueError, match="GitHub expressions"):
        generate_github_workflow(spec, tmp_path / "workflow.yml", repro_path="${{ secrets.EXAMPLE }}/repro.yml")
    assert not (tmp_path / "workflow.yml").exists()
