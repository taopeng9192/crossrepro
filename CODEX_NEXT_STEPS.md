# Work that still requires Codex / a real repository / real runners

## Updated status — 2026-09-18

Local review, fixes, full Windows tests (111 passed, 1 symlink test skipped),
three real examples, bundle checks and clean dev2 wheel installation are done.
See `VALIDATION_REPORT.md` and `CODE_REVIEW_REPORT.md`; do not restart from the
original dev0 recommendation below or treat the older Linux results as current.

Next external gate needs an explicitly selected GitHub repository and permission
to push/trigger CI. The repository root should be the `crossrepro/` directory,
so `.github/workflows/test.yml` and `pyproject.toml` are at the expected locations.
Do not upload `.venv`, caches or unrestricted raw logs. The prepared matrix runs
Windows/Linux/macOS with Python 3.10 and 3.12, real examples/bundles and clean
wheel installation. Inspect each artifact before considering a v0.1.0 release.

Current status: `LOCAL_WINDOWS_VALIDATED / HOSTED_MATRIX_PENDING`.
The local `crossrepro/` repository is initialized on `main`, but has no commit
or remote. No push, release or external submission has been performed.

## Original delivery next steps (historical context)

The environment-independent core is provided in this delivery. Do **not** mark
`v0.1.0` complete until the following are done in the real GitHub repository.

## Required engineering validation

1. Create/push the repository and install from a clean clone.
2. Run the full test suite on Windows, Linux and macOS.
3. Run all three examples on GitHub-hosted runners.
4. Confirm shell quoting/glob behavior on PowerShell and Bash.
5. Inspect generated `.crossrepro.zip` artifacts on each OS.
6. Fix every discovered platform issue and add a regression test.
7. Re-run all checks until green.
8. Only then tag/release `v0.1.0`.

## Required product validation after release

- use CrossRepro on real OSS bugs;
- collect real maintainer feedback;
- triage real issues;
- make follow-up releases;
- integrate Codex after deterministic reproduction, not inside verdict logic.

## Suggested first Codex task

```text
Take the supplied CrossRepro repository as the baseline.
Do not redesign product scope.
Run installation and the full test suite.
Fix all failures with regression tests.
Then validate on Windows, Ubuntu and macOS GitHub Actions runners.
Preserve deterministic verdict semantics and privacy fail-closed behavior.
Report every platform-specific change before preparing v0.1.0.
```
