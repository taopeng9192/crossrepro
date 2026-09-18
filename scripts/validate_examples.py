"""Run real examples and the capture -> replay -> bundle -> CI flow.

Run from the repository root after installing CrossRepro. Output must be a
repository-relative directory; previous ZIP artifacts are never overwritten.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import zipfile

import yaml

FAKE_VALUES = [b"TEST_ONLY_SECRET_123456", b"test@example.com"]


def run_cli(root: Path, *args: str) -> None:
    env = dict(os.environ)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env["PYTHONUTF8"] = "1"
    result = subprocess.run([sys.executable, "-m", "crossrepro.cli", *map(str, args)],
                            cwd=root, env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=120)
    if result.returncode:
        raise RuntimeError(f"CLI failed ({result.returncode}): {result.stdout}\n{result.stderr}")


def check_safe(data: bytes) -> None:
    if any(value in data for value in FAKE_VALUES):
        raise AssertionError("unsanitized fake fixture value in artifact")


def validate(root: Path, output: Path) -> dict:
    output = output.resolve()
    output.relative_to(root)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"validation output must be a new or empty directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, expected in [
        ("secret-redaction", "REPRODUCED"),
        ("missing-runtime", "ENVIRONMENT_BLOCKED"),
        ("shell-glob", "REPRODUCED" if platform.system() == "Windows" else "NOT_REPRODUCED"),
    ]:
        report = output / f"{name}.json"
        run_cli(root, "replay", f"examples/{name}/repro.yml", "--base-dir", ".", "--report", report)
        check_safe(report.read_bytes())
        payload = json.loads(report.read_text(encoding="utf-8"))
        actual = payload["result"]["verdict"]
        if actual != expected:
            raise AssertionError(f"{name}: expected {expected}, got {actual}")
        results[name] = {"verdict": actual, "exit_code": payload["execution"]["exit_code"]}

    capture = output / "capture"
    run_cli(root, "collect", "--command-text", "python examples/secret-redaction/emit.py", "--out", capture)
    run_cli(root, "replay", capture / "repro.yml", "--base-dir", ".", "--report", capture / "reports/local.json")
    local = json.loads((capture / "reports/local.json").read_text(encoding="utf-8"))
    if local["result"]["verdict"] != "REPRODUCED":
        raise AssertionError("captured spec failed to reproduce")
    bundle = output / "example.crossrepro.zip"
    run_cli(root, "pack", "--source", capture, "--output", bundle)
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        if not {"repro.yml", "manifest.json", "SHA256SUMS", "reports/local.json"} <= names:
            raise AssertionError("bundle is incomplete")
        for name in names:
            check_safe(archive.read(name))
        checksums = {}
        for line in archive.read("SHA256SUMS").decode("utf-8").splitlines():
            digest, name = line.split("  ", 1)
            checksums[name] = digest
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise AssertionError(f"checksum mismatch: {name}")
        if set(checksums) != names - {"SHA256SUMS"}:
            raise AssertionError("checksum coverage is incomplete")
        manifest = json.loads(archive.read("manifest.json"))
        if {item["path"] for item in manifest["files"]} != names - {"manifest.json", "SHA256SUMS"}:
            raise AssertionError("manifest coverage is incomplete")

    workflow = output / "crossrepro.yml"
    run_cli(root, "ci", capture / "repro.yml", "--output", workflow, "--install-source", ".")
    generated = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    if len(generated["jobs"]["replay"]["strategy"]["matrix"]["os"]) != 3:
        raise AssertionError("generated matrix is incomplete")
    summary = {"os": platform.system(), "python": platform.python_version(), "examples": results,
               "end_to_end": "PASS", "zip_privacy_scan": "PASS", "sha256_verification": "PASS",
               "workflow_yaml": "PASS", "hosted_workflow_execution": "NOT_RUN"}
    (output / "validation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(validate(Path.cwd().resolve(), arguments.output), indent=2))
