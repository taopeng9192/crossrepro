from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from crossrepro.replay.runner import ReplayExecution
from crossrepro.schema.models import BugSignature
from crossrepro.redact.engine import redact_data


class Verdict(str, Enum):
    REPRODUCED = "REPRODUCED"
    NOT_REPRODUCED = "NOT_REPRODUCED"
    ENVIRONMENT_BLOCKED = "ENVIRONMENT_BLOCKED"


@dataclass(slots=True)
class VerdictResult:
    verdict: Verdict
    checks: dict[str, bool]
    blocked_reason: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["verdict"] = self.verdict.value
        return redact_data(data)


def evaluate(execution: ReplayExecution, signature: BugSignature) -> VerdictResult:
    if execution.blocked_reason:
        return VerdictResult(
            verdict=Verdict.ENVIRONMENT_BLOCKED,
            checks={},
            blocked_reason=execution.blocked_reason,
        )

    checks: dict[str, bool] = {}
    if signature.exit_code:
        exit_signature = signature.exit_code
        if exit_signature.equals is not None:
            checks[f"exit_code_equals:{exit_signature.equals}"] = execution.exit_code == exit_signature.equals
        elif exit_signature.mode == "nonzero":
            checks["exit_code_nonzero"] = execution.exit_code not in (0, None)

    if signature.stdout:
        stdout = execution._raw_stdout if execution._raw_stdout is not None else execution.stdout
        for index, needle in enumerate(signature.stdout.contains, 1):
            checks[f"stdout_contains:{index}"] = needle in stdout
    if signature.stderr:
        stderr = execution._raw_stderr if execution._raw_stderr is not None else execution.stderr
        for index, needle in enumerate(signature.stderr.contains, 1):
            checks[f"stderr_contains:{index}"] = needle in stderr
    if signature.files:
        root = Path(execution.workdir)
        for value in [*signature.files.exists, *signature.files.missing]:
            try:
                (root / value).resolve().relative_to(root.resolve())
            except (ValueError, OSError, RuntimeError):
                return VerdictResult(Verdict.ENVIRONMENT_BLOCKED, {}, "file signature escapes workdir")
        for value in signature.files.exists:
            checks[f"file_exists:{value}"] = (root / value).exists()
        for value in signature.files.missing:
            checks[f"file_missing:{value}"] = not (root / value).exists()

    reproduced = bool(checks) and all(checks.values())
    return VerdictResult(
        verdict=Verdict.REPRODUCED if reproduced else Verdict.NOT_REPRODUCED,
        checks=checks,
    )
