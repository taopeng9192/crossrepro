# CrossRepro validation report

## Maintenance release validation — 2026-09-18 / 0.1.1

Status: **PUBLIC_REPOSITORY / V0.1.1_RELEASED / HOSTED_MATRIX_VALIDATED**.

Version 0.1.1 fixes bounded Windows timeout cleanup when detached children keep
capture-pipe handles open. The release commit
`5e76312b5b2be395ef523d3e72b2d9bba02a6393` passed GitHub Actions run
`35347745740` before annotated tag `v0.1.1` and the public Release were
created. Downloaded artifacts contain six JUnit reports: 684 test executions,
zero failures/errors, and six explicit skips across Windows, Ubuntu and macOS
with Python 3.10 and 3.12.

| Check | Observed result | Evidence |
|---|---|---|
| Local complete suite | **113 passed, 1 skipped**, exit 0 | `.validation/v0.1.1-full-tests-path/` |
| Local compilation | PASS | `python -m compileall -q src tests scripts` |
| Hosted release matrix | **6 / 6 PASS**; 684 executions, zero failures/errors, 6 skips | GitHub Actions run `35347745740`; downloaded artifacts in `../build_artifacts/hosted-ci-35347745740-20260918/` |
| Release wheel build and clean local validation | PASS | `../build_artifacts/release-0.1.1/crossrepro-0.1.1-py3-none-any.whl`; `scripts/validate_wheel.py` |
| Public release wheel validation | PASS: fresh venv imported `0.1.1`; `crossrepro --help` passed | `.validation/release-v0.1.1-public/` |

Release: `https://github.com/taopeng9192/crossrepro/releases/tag/v0.1.1`.
Published wheel SHA-256:
`c28599635aca851fbf7aeaf967b3c3a9618c0e20e97e296b4868c43497efac21`.
Issue `#1` records the detached-child trigger and was closed after the public
wheel validation. Case 001 is an isolated local evaluation of a public
agent-browser issue; it is not an upstream-confirmed reproduction, contributor
feedback, or a three-platform result. See `docs/cases/case-001-agent-browser-1407.md`.
Stage 10 now also has local Windows replay records for public uv and GitHub CLI
issues in `docs/cases/case-002-uv-21477.md` and
`docs/cases/case-003-gh-11402.md`; neither record constitutes upstream feedback
or multi-platform validation.

## Release validation — 2026-09-18 / 0.1.0

Status: **PUBLIC_REPOSITORY / V0.1.0_RELEASED / HOSTED_MATRIX_VALIDATED**.

The current source was tested on local Windows with Python 3.12.14. The public
repository is `https://github.com/taopeng9192/crossrepro`; its final
version/release-documentation commit passed the six-job hosted matrix at
`https://github.com/taopeng9192/crossrepro/actions/runs/35339802773` before
annotated tag `v0.1.0` and the public GitHub Release were created. The release
is `https://github.com/taopeng9192/crossrepro/releases/tag/v0.1.0`; its wheel
was downloaded from the public release URL into a fresh isolated venv and
verified by import and console entry point. The older report below describes
the original dev0 Linux snapshot only.

| Check | Observed result | Evidence |
|---|---|---|
| Original Windows baseline | 72 passed, 3 failed, 2 decode warnings | `../build_artifacts/baseline-windows-tests.txt` |
| New initial regression cases against original code | 18 failed before fixes | `../build_artifacts/regressions-before.txt` |
| Final full suite | **111 passed, 1 skipped**, exit 0 | `../build_artifacts/windows-dev2-final-tests.xml` and `.txt` |
| Statement coverage | **814 / 903 = 90.14%** | `../build_artifacts/coverage-windows-dev2-final.json` |
| Compile, indentation and dependency checks | PASS | activation command recorded below; `python -m pip check` returned `No broken requirements found` |
| Three examples and full capture/replay/pack flow | PASS | `.validation/windows-dev2-final/validation.json` |
| ZIP fixture-secret scan and all SHA-256 entries | PASS | `.validation/windows-dev2-final/example.crossrepro.zip` and validation JSON |
| Final workflow YAML structure | PASS (3 OS × 2 Python versions) | `.github/workflows/test.yml` parsed locally |
| Wheel build and byte comparison with source | PASS (26 Python files) | `../build_artifacts/release-0.1.0/crossrepro-0.1.0-py3-none-any.whl` |
| Clean venv install, isolated import, console entry, real capture/replay | PASS | `../build_artifacts/release-0.1.0/wheel-install.json` |
| Hosted release matrix Windows/Ubuntu/macOS × Python 3.10/3.12 | **6 / 6 PASS** | GitHub Actions run `35339802773`; downloaded artifacts in `../build_artifacts/hosted-ci-35339802773-20260918/` |
| Public release wheel install | PASS | Fresh isolated venv installed `0.1.0`; import and `crossrepro --help` succeeded |

The local Windows run skipped `test_pack_refuses_symlink_to_outside` because
this host denied symlink creation. The hosted matrix did not treat that local
result as a pass: Linux had one explicit skip in each Python version, while
Windows and macOS ran all 112 tests. All hosted jobs had zero failures/errors.
Other security unit tests include synthetic/mocked executions where appropriate;
the three examples, end-to-end flow and wheel-install capture/replay used real
subprocesses.

Current Windows results:

| Example | Exit code | Verdict |
|---|---:|---|
| secret-redaction | 3 | REPRODUCED |
| missing-runtime | none | ENVIRONMENT_BLOCKED |
| shell-glob | 2 | REPRODUCED |

Hosted example results match the intended platform distinction: secret-redaction
reproduced and missing-runtime was environment-blocked on every runner;
shell-glob reproduced on Windows and was not reproduced on Linux/macOS. Every
downloaded artifact passed the bundle privacy and SHA-256 checks; a search for
the fixture secret returned no matches.

Environment dependencies: Click 8.5.0, PyYAML 6.0.3, pytest 9.1.1,
pytest-cov 7.1.0, coverage 7.16.1. Tests prepended `.venv/Scripts` to the child
PATH so the examples' `python` command resolved to the project environment;
the final suite ran with `PYTHONUTF8=1`. No global PATH/Python/pip setting changed.
Clean wheel installation explicitly disabled host pip config and `--user`
inside that temporary subprocess after the first attempt exposed a host
configuration conflict. The successful clean install fetched declared runtime
dependencies and imported CrossRepro from the new venv, outside the source tree.

Wheel: `../build_artifacts/release-0.1.0/crossrepro-0.1.0-py3-none-any.whl`.
SHA-256: `cd676c6808d3f4534b6245f627ba1d28ff3d7933a2849563ad4a83e8aed17617`.
The wheel's 26 packaged Python files match the source bytes. Its metadata
declares `License-Expression: MIT` and includes `LICENSE`; the earlier
setuptools license-metadata deprecation warning is absent from this build.

Re-run from the `crossrepro/` project root in an activated environment:

```text
./.venv/Scripts/Activate.ps1  # PowerShell on Windows
python -m pytest --cov=crossrepro
python -m compileall -q src tests scripts
python scripts/validate_examples.py --output .validation/new-run
python -m pip wheel --no-deps . --wheel-dir dist
python scripts/validate_wheel.py --wheel-dir dist --report .validation/wheel.json
```

Do not promote the historical Linux result below to validation of this revision.
The public `main` branch contains the version/release-documentation commit
`86bc39042ab9dbabb028cf206c5a1d70d54c7d19`. Its six-job workflow passed before
annotated tag `v0.1.0` and the non-draft, non-prerelease GitHub Release were
created. The published wheel SHA-256 is
`cd676c6808d3f4534b6245f627ba1d28ff3d7933a2849563ad4a83e8aed17617`.

## Historical report — original 2026-09-17 dev0 delivery

Validation date: **2026-09-17**
Snapshot version: **0.1.0.dev0**

## Result

The environment-independent v0.1 core in this delivery has been implemented and
reviewed locally. It is **not** being labeled `v0.1.0` yet because real Windows,
macOS and GitHub-hosted runner validation is still required.

## Automated validation completed

- Python source/test compilation: **PASS**
- `pytest`: **75 tests PASS**
- statement coverage for `crossrepro`: **93%**
- `tabnanny`: **PASS**
- residual `TODO/FIXME/XXX/NotImplemented/breakpoint` scan: **PASS**
- wheel build (`py3-none-any`): **PASS**
- wheel import from isolated target directory: **PASS**
- console entry point `crossrepro --help`: **PASS**
- module entry point `python -m crossrepro.cli --help`: **PASS**
- local integration replay: **PASS**
- bundle ZIP construction: **PASS**
- bundle SHA-256 verification: **PASS**
- fake-secret leak scan: **PASS**
- generated GitHub Actions YAML parse: **PASS**

## Local example results

On the current Linux execution environment:

| Example | Result |
|---|---|
| `secret-redaction` | `REPRODUCED` |
| `missing-runtime` | `ENVIRONMENT_BLOCKED` |
| `shell-glob` | `NOT_REPRODUCED` |

The `shell-glob` example is intentionally expected to differ on PowerShell, but
that Windows behavior is **not claimed as validated** until a real Windows
runner executes it.

## End-to-end flow validated locally

The following flow was executed successfully:

```text
collect
  -> sanitized evidence
  -> generated repro.yml
  -> replay
  -> deterministic verdict
  -> pack
  -> manifest + SHA256SUMS
  -> ZIP secret scan
  -> CI workflow generation
```

The test fixture emitted a fake API key and email. Neither original value was
present in the final ZIP.

## Packaging validation

A pure-Python wheel was built successfully:

```text
crossrepro-0.1.0.dev0-py3-none-any.whl
```

The wheel was installed into a separate target directory with `--no-deps` and
successfully imported.

### Clean-venv caveat in this container

A newly created venv in this execution container exposes an incomplete system
`setuptools` namespace without `setuptools.build_meta`, so a clean-venv editable
install could not be used as a trustworthy project check here. The project
itself successfully built a wheel using the active build environment. A truly
clean Windows/Linux/macOS clone/install remains a release gate.

The container also has an unrelated global `moviepy` / `pillow` dependency
conflict. It is not a CrossRepro dependency and is not treated as a CrossRepro
failure.

## Security/correctness issues found during self-review and fixed

1. Capture output could have recursively deleted an arbitrary existing
   directory. It now deletes only a directory carrying CrossRepro's state
   marker; non-CrossRepro non-empty directories are refused.
2. A command returning exit code `0` previously could create a meaningless
   automatic bug signature. It now requires manual signature authoring.
3. A command containing a secret could be redacted into a non-replayable
   command. CrossRepro now saves sanitized evidence but does not auto-create
   `repro.yml` in that case.
4. Timed-out captures no longer create an invalid automatic signature.
5. `workdir` and file-signature paths reject absolute paths and `..` traversal.
6. Git/environment structured metadata now passes through redaction before it
   is stored.
7. Common naked developer tokens (`sk-...`, GitHub tokens, Stripe-style keys)
   and common user-home paths gained redaction coverage.
8. Bundle output is forbidden inside its source directory, avoiding recursive
   self-inclusion.
9. A bundle must contain `repro.yml`.
10. Internal `.crossrepro-state` markers are excluded from portable bundles and
    checksums.
11. Invalid schemas are converted to readable CLI errors instead of raw
    tracebacks.
12. Business verdicts remain independent of CI infrastructure failure: a
    `REPRODUCED` result is a valid experiment outcome.

## What still requires Codex / real environments

Before tagging `v0.1.0`, the real repository must complete:

- clean-clone installation on Windows, Linux and macOS;
- full 75+ test suite on all three operating systems;
- real PowerShell shell/glob validation;
- generated GitHub Actions workflow on `windows-latest`, `ubuntu-latest`, and
  `macos-latest`;
- inspection of artifacts produced on each OS;
- regression tests for every platform-specific issue discovered;
- final release/tag only after all of the above are green.

## Scope statement

This report validates the code that can reasonably be tested without external
platforms/accounts. It does **not** claim external adoption, OpenAI program
eligibility/selection, real-world maintainer impact, or Windows/macOS runner
success.
