# Work that still requires Codex / a real repository / real runners

## Updated status — 2026-09-18

Local review, fixes, full Windows tests (111 passed, 1 symlink test skipped),
three real examples, bundle checks and clean wheel installation are done. The
public repository and its first six-job GitHub Actions matrix are also complete:
all six jobs passed, and downloaded artifacts were inspected. See
`VALIDATION_REPORT.md` and `CODE_REVIEW_REPORT.md`; do not restart from the
original dev0 recommendation below or treat the older Linux results as current.

The repository is `https://github.com/taopeng9192/crossrepro`; the first hosted
matrix is `https://github.com/taopeng9192/crossrepro/actions/runs/35338776666`.
The immediate release gate is the version-commit matrix, followed by tag
`v0.1.0`, the GitHub Release and a clean remote-wheel install check.

Current status: `PUBLIC_REPOSITORY / HOSTED_MATRIX_VALIDATED / FINAL_CI_GATE`.

## Original delivery next steps (historical context)

The environment-independent core is provided in this delivery. Do **not** mark
`v0.1.0` complete until the following are done in the real GitHub repository.

## Required engineering validation

1. Run the release-version workflow and inspect its six artifacts.
2. Tag and publish `v0.1.0` with the verified wheel attached.
3. Install that public wheel in a fresh environment.
4. Begin real OSS validation only after the release exists.

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
