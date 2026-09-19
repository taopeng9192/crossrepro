from __future__ import annotations

import sys
import json
from pathlib import Path
from types import ModuleType

from crossrepro.capture.runner import default_shell
from crossrepro.repair.models import FixStatus, PatchProposal
from crossrepro.repair.patch import PatchError, stage_patch
from crossrepro.repair.providers import FilePatchProvider, OpenAIRepairProvider
from crossrepro.repair.runner import fix


class FakeProvider:
    def __init__(self, patch: str) -> None:
        self.patch = patch
        self.prompts: list[str] = []

    def propose(self, *, prompt: str) -> PatchProposal:
        self.prompts.append(prompt)
        return PatchProposal(summary="Return the correct value.", patch=self.patch)


def python_command(code: str) -> str:
    executable = str(sys.executable)
    if default_shell() in {"pwsh", "powershell"}:
        return f"& '{executable.replace("'", "''")}' -c '{code}'"
    return f'"{executable}" -c "{code}"'


def fixture_project(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "target"
    repo.mkdir()
    (repo / "app.py").write_text("def answer():\n    return 1\n", encoding="utf-8")
    command = python_command("from app import answer; assert answer() == 2")
    return repo, command


def answer_patch(value: int) -> str:
    return """--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def answer():
-    return 1
+    return {value}
""".format(value=value)


def test_stage_patch_refuses_paths_outside_repository(tmp_path: Path):
    patch = """--- a/../secret.py
+++ b/../secret.py
@@ -1 +1 @@
-x
+y
"""
    with __import__("pytest").raises(PatchError, match="relative path"):
        stage_patch(tmp_path, patch)


def test_stage_patch_refuses_file_not_sent_to_provider(tmp_path: Path):
    (tmp_path / "app.py").write_text("x\n", encoding="utf-8")
    patch = """--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-x
+y
"""
    with __import__("pytest").raises(PatchError, match="not supplied"):
        stage_patch(tmp_path, patch, allowed_paths={"other.py"})


def test_fix_candidate_does_not_modify_target(tmp_path: Path):
    repo, command = fixture_project(tmp_path)
    output = tmp_path / "result"
    provider = FakeProvider(answer_patch(2))

    result = fix(
        repo=repo,
        test_command=command,
        provider=provider,
        patch_path=output / "candidate.patch",
        report_path=output / "fix-report.json",
        apply=False,
        timeout=15,
    )

    assert result.status is FixStatus.CANDIDATE
    assert "return 1" in (repo / "app.py").read_text(encoding="utf-8")
    assert (output / "candidate.patch").exists()
    assert (output / "fix-report.json").exists()
    assert "TEST COMMAND:" in provider.prompts[0]


def test_fix_applies_only_a_verified_patch(tmp_path: Path):
    repo, command = fixture_project(tmp_path)
    output = tmp_path / "result"

    result = fix(
        repo=repo,
        test_command=command,
        provider=FakeProvider(answer_patch(2)),
        patch_path=output / "candidate.patch",
        report_path=output / "fix-report.json",
        apply=True,
        timeout=15,
    )

    assert result.status is FixStatus.FIXED
    assert "return 2" in (repo / "app.py").read_text(encoding="utf-8")
    assert result.changed_files == ["app.py"]


def test_fix_reverts_a_patch_when_verification_fails(tmp_path: Path):
    repo, command = fixture_project(tmp_path)
    output = tmp_path / "result"

    result = fix(
        repo=repo,
        test_command=command,
        provider=FakeProvider(answer_patch(3)),
        patch_path=output / "candidate.patch",
        report_path=output / "fix-report.json",
        apply=True,
        timeout=15,
    )

    assert result.status is FixStatus.VERIFICATION_FAILED
    assert "return 1" in (repo / "app.py").read_text(encoding="utf-8")


def test_openai_provider_requests_a_non_stored_patch_only_response(monkeypatch):
    calls: list[dict] = []

    class Responses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return type("Response", (), {"output_text": json.dumps({"summary": "fix", "patch": "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-x\n+y"})})()

    class Client:
        def __init__(self, *, api_key):
            assert api_key == "test-key"
            self.responses = Responses()

    module = ModuleType("openai")
    module.OpenAI = Client
    monkeypatch.setitem(sys.modules, "openai", module)

    proposal = OpenAIRepairProvider(model="test-model", api_key="test-key").propose(prompt="repair this")

    assert proposal.summary == "fix"
    assert calls[0]["model"] == "test-model"
    assert calls[0]["store"] is False
    assert "filesystem" in calls[0]["instructions"]


def test_file_patch_provider_reuses_the_reviewed_patch(tmp_path: Path):
    patch_file = tmp_path / "candidate.patch"
    patch_file.write_text(answer_patch(2), encoding="utf-8")

    proposal = FilePatchProvider(patch_file).propose(prompt="ignored")

    assert proposal.patch == answer_patch(2)
    assert "candidate.patch" in proposal.summary
