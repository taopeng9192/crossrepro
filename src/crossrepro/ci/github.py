from __future__ import annotations

from pathlib import Path
import yaml

from crossrepro.schema.models import ReproSpec
from crossrepro.redact.engine import contains_high_risk_secret

DEFAULT_PLATFORMS = ["windows-latest", "ubuntu-latest", "macos-latest"]


def generate_github_workflow(spec: ReproSpec, output_path: Path, *, repro_path: str = "repro.yml", install_source: str = ".") -> Path:
    if any("${{" in value or contains_high_risk_secret(value) for value in (repro_path, install_source)):
        raise ValueError("workflow inputs cannot contain GitHub expressions or detected credentials")
    platforms = spec.platforms or DEFAULT_PLATFORMS
    # User-supplied paths are data in env, never interpolated shell source.
    steps = [
        {"name": "Checkout", "uses": "actions/checkout@v4"},
        {"name": "Setup Python", "uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
        {"name": "Install CrossRepro", "env": {"CROSSREPRO_INSTALL_SOURCE": install_source},
         "run": 'python -c "import os, subprocess, sys; subprocess.run([sys.executable, \'-m\', \'pip\', \'install\', \'--\', os.environ[\'CROSSREPRO_INSTALL_SOURCE\']], check=True)"'},
        {"name": "Replay", "env": {"CROSSREPRO_SPEC": repro_path},
         "run": 'python -c "import os, subprocess, sys; subprocess.run([sys.executable, \'-m\', \'crossrepro.cli\', \'replay\', \'--base-dir\', \'.\', \'--report\', \'report.json\', \'--\', os.environ[\'CROSSREPRO_SPEC\']], check=True)"'},
        {"name": "Write summary", "if": "always()",
         "run": 'python -c "import os; from pathlib import Path; from crossrepro.ci.summary import write_summary; write_summary(Path(\'report.json\'), Path(os.environ[\'GITHUB_STEP_SUMMARY\']))"'},
        {"name": "Upload report", "if": "always()", "uses": "actions/upload-artifact@v4",
         "with": {"name": "crossrepro-${{ matrix.os }}", "path": "report.json", "if-no-files-found": "error"}},
    ]
    workflow = {"name": "CrossRepro", "on": {"workflow_dispatch": None, "pull_request": None},
                "permissions": {"contents": "read"},
                "jobs": {"replay": {"name": "CrossRepro / ${{ matrix.os }}", "runs-on": "${{ matrix.os }}",
                                    "strategy": {"fail-fast": False, "matrix": {"os": platforms}}, "steps": steps}}}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(workflow, sort_keys=False, width=120), encoding="utf-8")
    return output_path
