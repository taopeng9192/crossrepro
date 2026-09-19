from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from .models import PatchProposal


class RepairProvider(Protocol):
    def propose(self, *, prompt: str) -> PatchProposal:
        """Return one proposed unified diff without applying it."""


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
            payload = json.loads(response.output_text)
            summary = payload["summary"]
            patch = payload["patch"]
        except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("OpenAI provider returned an invalid repair proposal") from exc
        if not isinstance(summary, str) or not isinstance(patch, str):
            raise ValueError("OpenAI provider proposal fields must be strings")
        return PatchProposal(summary=summary, patch=patch)


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
