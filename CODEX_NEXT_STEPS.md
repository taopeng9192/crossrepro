# Work that still requires Codex / a real repository / real runners

## Updated status — 2026-09-18

The current release is `v0.1.1`, published at
`https://github.com/taopeng9192/crossrepro/releases/tag/v0.1.1`. Its
release commit passed GitHub Actions run
`https://github.com/taopeng9192/crossrepro/actions/runs/35347745740`: all six
Windows/Ubuntu/macOS × Python 3.10/3.12 jobs succeeded. Downloaded JUnit
artifacts show 684 executions with zero failures/errors and six explicit
skips. The public wheel was fetched from that Release into a fresh venv,
imported as `0.1.1`, and its `crossrepro --help` entry point succeeded; SHA-256
is `c28599635aca851fbf7aeaf967b3c3a9618c0e20e97e296b4868c43497efac21`.

Stage 10 now has five documented isolated local cases in four external
ecosystems: `docs/cases/case-001-agent-browser-1407.md` through
`docs/cases/case-005-npm-7830.md`. Three have Windows `REPRODUCED` replay
verdicts (uv #21477, gh #11402, npm #7830); case 001 is a timeout observation,
and case 004 records a successful-exit/missing-output condition that v1 cannot
express as a signature. Case 001 found a collection-timeout cleanup defect in
CrossRepro and resulted in v0.1.1. None is upstream confirmation, upstream
feedback, or external adoption. The related project issue `#1` is closed after
release validation.

Local review, fixes, full Windows tests (111 passed, 1 symlink test skipped),
three real examples, bundle checks and clean wheel installation are done. The
public repository and its first six-job GitHub Actions matrix are also complete:
all six jobs passed, and downloaded artifacts were inspected. See
`VALIDATION_REPORT.md` and `CODE_REVIEW_REPORT.md`; do not restart from the
original dev0 recommendation below or treat the older Linux results as current.

The repository is `https://github.com/taopeng9192/crossrepro`; release
`v0.1.0` is published at
`https://github.com/taopeng9192/crossrepro/releases/tag/v0.1.0`. Its final
version-commit matrix passed at
`https://github.com/taopeng9192/crossrepro/actions/runs/35339802773`: all six
Windows/Ubuntu/macOS × Python 3.10/3.12 jobs completed successfully. The
published wheel was fetched from the release URL into a new isolated venv,
imported as `0.1.0`, and its `crossrepro --help` entry point succeeded.

Historical v0.1.0 status: `PUBLIC_REPOSITORY / V0.1.0_RELEASED / HOSTED_MATRIX_VALIDATED`.
Current status: `PUBLIC_REPOSITORY / V0.1.1_RELEASED / HOSTED_MATRIX_VALIDATED`.

## Original delivery next steps (historical context)

The environment-independent core is provided in this delivery. Do **not** mark
`v0.1.0` complete until the following are done in the real GitHub repository.

## Completed engineering validation

1. The release-version workflow passed and all six downloaded JUnit reports
   have zero failures/errors (672 test executions in total; two Linux symlink
   skips are explicit).
2. Annotated tag `v0.1.0` resolves to commit
   `86bc39042ab9dbabb028cf206c5a1d70d54c7d19`; the public GitHub Release has
   the verified wheel attached.
3. The wheel installed from its public release URL in a fresh isolated venv;
   the installed version and console entry point were verified.
4. Stage 10 has five local case records across external projects, but no
   independent external usage, maintainer feedback, or upstream interaction is
   claimed yet.

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
