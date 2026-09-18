"""Regression expectations from the privacy contract and reproduction protocol."""
import json
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from crossrepro.bundle.builder import UnsafeBundleError, build_bundle
from crossrepro.capture.runner import CommandResult
from crossrepro.cli import main
from crossrepro.redact.engine import contains_high_risk_secret, redact_text
from crossrepro.replay.runner import replay
from crossrepro.schema.loader import ReproLoadError, load_repro
from crossrepro.schema.models import BugSignature, CommandSpec, ExitCodeSignature, ReproSpec, StreamSignature
from crossrepro.schema.validator import InvalidReproSpec, validate_repro
from crossrepro.verdict.evaluator import Verdict, evaluate

FAKE = "TEST_ONLY_AUDIT_SECRET_987654"
VALID = "version: 1\nname: example\ncommand: {run: 'echo ok'}\nbug_signature: {exit_code: {equals: 1}}\n"


def make_spec(**changes):
    values = dict(version=1, name="test", workdir=".", setup_commands=[],
                  default_command=CommandSpec("echo ok"), platform_commands={},
                  bug_signature=BugSignature(exit_code=ExitCodeSignature(equals=1)),
                  required_commands=[], platforms=[])
    values.update(changes)
    return ReproSpec(**values)


def fake_run(command, **kwargs):
    return CommandResult(command, "pwsh", 1, f"api_key={FAKE}", "", "start", "end", 1)


def test_report_redacts_all_fields(monkeypatch, tmp_path):
    repro = tmp_path / "repro.yml"
    repro.write_text(VALID.replace("echo ok", f"echo api_key={FAKE}"), encoding="utf-8")
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda _: "pwsh")
    monkeypatch.setattr("crossrepro.replay.runner.run_command", fake_run)
    report = tmp_path / "report.json"
    result = CliRunner().invoke(main, ["replay", str(repro), "--base-dir", str(tmp_path), "--report", str(report)])
    assert result.exit_code == 0, result.output
    assert FAKE not in report.read_text(encoding="utf-8")
    assert json.loads(report.read_text(encoding="utf-8"))["result"]["verdict"] == "REPRODUCED"


def test_setup_failure_reason_is_redacted(monkeypatch, tmp_path):
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda _: "pwsh")
    monkeypatch.setattr("crossrepro.replay.runner.run_command", fake_run)
    execution = replay(make_spec(setup_commands=[f"setup --api_key={FAKE}"]), base_dir=tmp_path)
    assert execution.blocked_reason
    assert FAKE not in execution.blocked_reason


def test_signature_uses_original_output_without_persisting_it(monkeypatch, tmp_path):
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda _: "pwsh")
    monkeypatch.setattr("crossrepro.replay.runner.run_command", fake_run)
    spec = make_spec(bug_signature=BugSignature(stdout=StreamSignature([FAKE])))
    execution = replay(spec, base_dir=tmp_path)
    assert evaluate(execution, spec.bug_signature).verdict == Verdict.REPRODUCED
    assert FAKE not in json.dumps(execution.to_dict())
    assert FAKE not in repr(execution)
    wrong = BugSignature(stdout=StreamSignature(["TEST_ONLY_DIFFERENT_SECRET_987654"]))
    assert evaluate(execution, wrong).verdict == Verdict.NOT_REPRODUCED


@pytest.mark.parametrize("header", ["Cookie: session=", "Set-Cookie: session=", "Authorization: Basic "])
def test_headers_are_redacted_and_rescannable(header):
    text = header + FAKE
    assert contains_high_risk_secret(text)
    result = redact_text(text)
    assert FAKE not in result.text
    assert not contains_high_risk_secret(result.text)


def test_json_escaped_windows_home_is_redacted():
    text = json.dumps({"path": r"C:\Users\SyntheticAuditUser\project"})
    assert "SyntheticAuditUser" not in redact_text(text).text


@pytest.mark.parametrize("filename", [".env", "output.csv", "credentials", "program.py"])
def test_pack_scans_every_included_text_file(tmp_path, filename):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text(VALID, encoding="utf-8")
    (source / filename).write_text(f"api_key={FAKE}", encoding="utf-8")
    with pytest.raises(UnsafeBundleError):
        build_bundle(source, tmp_path / "out.zip")
    assert not (tmp_path / "out.zip").exists()


def test_pack_refuses_unscannable_content(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text(VALID, encoding="utf-8")
    (source / "data.bin").write_bytes(b"\xff\xfe" + FAKE.encode())
    with pytest.raises(UnsafeBundleError):
        build_bundle(source, tmp_path / "out.zip")


def test_pack_validates_protocol(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text("version: 1\n", encoding="utf-8")
    with pytest.raises((ReproLoadError, InvalidReproSpec, ValueError)):
        build_bundle(source, tmp_path / "out.zip")


def test_pack_does_not_mutate_source_when_output_is_invalid(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text(VALID, encoding="utf-8")
    with pytest.raises(ValueError):
        build_bundle(source, source / "out.zip")
    assert {p.name for p in source.iterdir()} == {"repro.yml"}


@pytest.mark.parametrize("field,value", [("version", "true"), ("workdir", "'C:outside'"), ("workdir", "'\\outside'")])
def test_schema_rejects_invalid_version_and_windows_paths(tmp_path, field, value):
    text = VALID.replace("version: 1", "version: true") if field == "version" else VALID + f"workdir: {value}\n"
    path = tmp_path / "repro.yml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises((ReproLoadError, InvalidReproSpec)):
        validate_repro(load_repro(path))


def test_schema_rejects_misspelled_signature(tmp_path):
    path = tmp_path / "repro.yml"
    path.write_text(VALID.replace("bug_signature: {exit_code: {equals: 1}}", "bug_signature: {exit_code: {equals: 1}, stderrr: {contains: [important]}}"), encoding="utf-8")
    with pytest.raises((ReproLoadError, InvalidReproSpec)):
        validate_repro(load_repro(path))


def test_capture_refuses_unknown_files_in_marked_output(monkeypatch, tmp_path):
    out = tmp_path / "capture"
    out.mkdir()
    (out / ".crossrepro-state").write_text("crossrepro-state-v1\n", encoding="utf-8")
    (out / "valuable.txt").write_text("keep me", encoding="utf-8")
    result = CliRunner().invoke(main, ["collect", "--command-text", "echo ok", "--out", str(out)])
    assert result.exit_code != 0
    assert (out / "valuable.txt").read_text(encoding="utf-8") == "keep me"


def test_pack_checksum_and_manifest_cover_exact_bytes(tmp_path):
    import hashlib
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text(VALID, encoding="utf-8")
    (source / "log.csv").write_text("field,value\n", encoding="utf-8")
    output = build_bundle(source, tmp_path / "out.zip")
    with zipfile.ZipFile(output) as archive:
        lines = archive.read("SHA256SUMS").decode().splitlines()
        checks = dict(line.split("  ", 1)[::-1] for line in lines)
        assert set(checks) == set(archive.namelist()) - {"SHA256SUMS"}
        for name, digest in checks.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    assert set(p.name for p in source.iterdir()) == {"repro.yml", "log.csv"}


def test_pack_refuses_symlink_to_outside(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text(VALID, encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("private file", encoding="utf-8")
    try:
        (source / "linked.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is not permitted on this runner")
    with pytest.raises(UnsafeBundleError):
        build_bundle(source, tmp_path / "out.zip")


def test_launch_permission_error_is_environment_blocked(monkeypatch, tmp_path):
    monkeypatch.setattr("crossrepro.replay.runner.resolve_shell", lambda _: "pwsh")
    def denied(*args, **kwargs):
        raise PermissionError("access denied")
    monkeypatch.setattr("crossrepro.replay.runner.run_command", denied)
    execution = replay(make_spec(), base_dir=tmp_path)
    assert evaluate(execution, make_spec().bug_signature).verdict == Verdict.ENVIRONMENT_BLOCKED


def test_capture_metadata_stays_valid_json_after_redaction(monkeypatch, tmp_path):
    from crossrepro.redact.engine import redact_json
    payload = {"path": r"C:\Users\SyntheticAuditUser\project", "header": f"Cookie: session={FAKE}", "name": 'quoted"name'}
    redacted = redact_json(payload)
    decoded = json.loads(redacted.text)
    assert FAKE not in redacted.text
    assert "SyntheticAuditUser" not in redacted.text
    assert decoded["name"] == payload["name"]


def test_argument_mode_preserves_literal_powershell_arguments(tmp_path):
    import shutil
    import subprocess
    import sys
    from crossrepro.cli import command_from_parts
    from crossrepro.capture.runner import run_command
    if not shutil.which("pwsh"):
        pytest.skip("PowerShell is unavailable")
    arguments = ["a b", "a'b", 'a"b', "$HOME", "*.md", "semi;colon"]
    command = command_from_parts((sys.executable, "-c", "import sys,json;print(json.dumps(sys.argv[1:]))", *arguments), "pwsh")
    result = run_command(command, cwd=tmp_path, shell="pwsh", timeout=15)
    assert result.exit_code == 0
    assert json.loads(result.stdout) == arguments


def test_json_secret_assignment_is_detected():
    text = json.dumps({"api_key": FAKE})
    assert contains_high_risk_secret(text)
    assert FAKE not in redact_text(text).text


def test_duplicate_yaml_signature_cannot_silently_override(tmp_path):
    path = tmp_path / "repro.yml"
    path.write_text(VALID + "bug_signature: {exit_code: {equals: 0}}\n", encoding="utf-8")
    with pytest.raises(ReproLoadError, match="duplicate"):
        load_repro(path)
