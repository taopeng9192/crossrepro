from pathlib import Path
import json

from crossrepro.constants import PLATFORM_KEYS, SUPPORTED_SHELLS
from crossrepro.verdict.evaluator import Verdict


def write_summary(report: Path, output: Path) -> None:
    payload = json.loads(report.read_text(encoding="utf-8"))
    execution = payload["execution"]
    platform = execution["platform"]
    shell = execution["shell"]
    verdict = Verdict(payload["result"]["verdict"]).value
    if platform not in PLATFORM_KEYS or (shell is not None and shell not in SUPPORTED_SHELLS):
        raise ValueError("unexpected platform/shell in report")
    # Only enumerated values are rendered; never echo commands or error text.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(f"\n| Platform | Shell | Verdict |\n|---|---|---|\n| {platform} | {shell or 'unavailable'} | {verdict} |\n")
