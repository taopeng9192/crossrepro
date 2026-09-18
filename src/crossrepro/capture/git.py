from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def run_git(cwd: Path, *args: str) -> tuple[int, str]:
    executable = shutil.which("git")
    if not executable:
        return 127, ""
    try:
        completed = subprocess.run(
            [executable, *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    output = completed.stdout or ""
    return completed.returncode, output if "--porcelain" in args else output.strip()


def collect_git_context(cwd: Path) -> dict | None:
    code, inside = run_git(cwd, "rev-parse", "--is-inside-work-tree")
    if code != 0 or inside != "true":
        return None
    _, branch = run_git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    _, commit = run_git(cwd, "rev-parse", "HEAD")
    _, status = run_git(cwd, "status", "--porcelain", "-z")
    changed_files: list[str] = []
    entries = iter(status.split("\0"))
    for line in entries:
        if len(line) >= 4:
            changed_files.append(line[3:])
            if "R" in line[:2] or "C" in line[:2]:
                next(entries, None)  # -z puts the destination first, then source.
    return {
        "branch": branch,
        "commit": commit,
        "dirty": bool(status),
        "changed_files": changed_files,
    }
