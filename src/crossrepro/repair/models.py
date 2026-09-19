from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class FixStatus(str, Enum):
    FIXED = "FIXED"
    CANDIDATE = "CANDIDATE"
    BASELINE_PASSED = "BASELINE_PASSED"
    PATCH_REJECTED = "PATCH_REJECTED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    PROVIDER_ERROR = "PROVIDER_ERROR"


@dataclass(slots=True)
class PatchProposal:
    summary: str
    patch: str


@dataclass(slots=True)
class FixResult:
    status: FixStatus
    summary: str
    baseline_exit_code: int | None
    verification_exit_code: int | None = None
    patch_path: str | None = None
    changed_files: list[str] = field(default_factory=list)
    detail: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data
