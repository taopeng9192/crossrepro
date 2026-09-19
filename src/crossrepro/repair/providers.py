from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Protocol

from .models import PatchProposal


class RepairProvider(Protocol):
    def propose(self, *, prompt: str) -> PatchProposal:
        """Return one proposed unified diff without applying it."""


def _proposal_from_json(text: str, provider_name: str) -> PatchProposal:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3].rstrip()
    try:
        payload = json.loads(text)
        summary = payload["summary"]
        patch = payload["patch"]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{provider_name} returned an invalid repair proposal") from exc
    if not isinstance(summary, str) or not isinstance(patch, str):
        raise ValueError(f"{provider_name} proposal fields must be strings")
    return PatchProposal(summary=summary, patch=patch)


class CodexCliRepairProvider:
    """Use a locally authenticated Codex CLI in a read-only workspace."""

    def __init__(self, *, repo: Path, timeout: int, model: str | None = None) -> None:
        self.repo = repo
        self.timeout = timeout
        self.model = model

    def propose(self, *, prompt: str) -> PatchProposal:
        executable = shutil.which("codex")
        if not executable:
            raise ValueError("Codex CLI was not found on PATH")
        output = tempfile.NamedTemporaryFile(prefix="crossrepro-codex-", suffix=".json", delete=False)
        output.close()
        args = [
            executable,
            "exec",
            "--sandbox",
            "read-only",
            "--ignore-rules",
            "--ephemeral",
            "--skip-git-repo-check",
            "--cd",
            str(self.repo),
            "--output-last-message",
            output.name,
        ]
        if self.model:
            args.extend(["--model", self.model])
        args.append("-")
        try:
            completed = subprocess.run(
                args,
                input=prompt,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
            if completed.returncode != 0:
                raise ValueError("Codex CLI did not complete the repair proposal")
            return _proposal_from_json(Path(output.name).read_text(encoding="utf-8"), "Codex CLI")
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Codex CLI timed out while proposing a repair") from exc
        finally:
            Path(output.name).unlink(missing_ok=True)


class OpenAIRepairProvider:
    """Small adapter around the OpenAI Responses API.

    The provider has no filesystem or shell tools. It receives only the prompt
    prepared by CrossRepro and can only return a JSON patch proposal.
    """

    def __init__(self, *, model: str, api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def propose(self, *, prompt: str) -> PatchProposal:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for provider=openai")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ValueError("install the optional agent dependency: pip install 'crossrepro[agent]'") from exc

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            instructions=(
                "You repair software from a failing test. Return only JSON with string fields "
                "'summary' and 'patch'. 'patch' must be a unified diff. Modify only files supplied "
                "in the project context. Do not use Markdown fences. Do not propose commands, credentials, "
                "dependency upgrades, generated files, or unrelated formatting changes. You have no shell, "
                "filesystem, network, or patch-application tools."
            ),
            input=prompt,
            store=False,
        )
        try:
            return _proposal_from_json(response.output_text, "OpenAI provider")
        except AttributeError as exc:
            raise ValueError("OpenAI provider returned an invalid repair proposal") from exc


class FilePatchProvider:
    """Apply a previously reviewed candidate through the same verifier."""

    def __init__(self, patch_file: Path) -> None:
        self.patch_file = patch_file

    def propose(self, *, prompt: str) -> PatchProposal:
        try:
            patch = self.patch_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"could not read patch file: {self.patch_file}") from exc
        return PatchProposal(summary=f"Apply reviewed patch from {self.patch_file.name}.", patch=patch)
