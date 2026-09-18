# CrossRepro validation report

## Current revision — 2026-09-18 / 0.1.0.dev2

Status: **LOCAL_WINDOWS_VALIDATED / HOSTED_MATRIX_PENDING**.

The current source was tested on local Windows with Python 3.12.14. No hosted
Windows, Linux or macOS run is claimed for this revision. The older report below
describes the original dev0 Linux snapshot only.

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
| Wheel build and byte comparison with source | PASS (26 Python files) | `../build_artifacts/validated-dev2/crossrepro-0.1.0.dev2-py3-none-any.whl` |
| Clean venv install, isolated import, console entry, real capture/replay | PASS | `../build_artifacts/validated-dev2/wheel-install.json` |

The skipped test is `test_pack_refuses_symlink_to_outside`: this host denied
symlink creation. It was not relabeled as a pass. Other security unit tests
include synthetic/mocked executions where appropriate; the three examples,
end-to-end flow and wheel-install capture/replay used real subprocesses.

Current Windows results:

| Example | Exit code | Verdict |
|---|---:|---|
| secret-redaction | 3 | REPRODUCED |
| missing-runtime | none | ENVIRONMENT_BLOCKED |
| shell-glob | 2 | REPRODUCED |

Environment dependencies: Click 8.5.0, PyYAML 6.0.3, pytest 9.1.1,
pytest-cov 7.1.0, coverage 7.16.1. Tests prepended `.venv/Scripts` to the child
PATH so the examples' `python` command resolved to the project environment;
the final suite ran with `PYTHONUTF8=1`. No global PATH/Python/pip setting changed.
Clean wheel installation explicitly disabled host pip config and `--user`
inside that temporary subprocess after the first attempt exposed a host
configuration conflict. The successful clean install fetched declared runtime
dependencies and imported CrossRepro from the new venv, outside the source tree.

Wheel: `../build_artifacts/validated-dev2/crossrepro-0.1.0.dev2-py3-none-any.whl`.
SHA-256: `2f6c0411276da8bce9529e5ec0b4b9dd1ddc54934240bde0a4bae62c82390eb2`.
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
Before v0.1.0: run the updated six-job Windows/Linux/macOS × Python 3.10/3.12
workflow in an authorized repository, inspect reports/bundles/wheel artifacts,
resolve failures and the symlink coverage gap, then obtain release authorization.
The local repository is initialized on `main`, but has no commit, configured
remote, tag, publication or hosted CI result.

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
