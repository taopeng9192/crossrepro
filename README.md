# CrossRepro

[![Test](https://github.com/taopeng9192/crossrepro/actions/workflows/test.yml/badge.svg)](https://github.com/taopeng9192/crossrepro/actions/workflows/test.yml)

> Turn “it fails on my machine” into a privacy-safe, portable, cross-platform reproduction.

CrossRepro records a failing CLI/build/test command, minimizes and redacts the
evidence, describes the failure in `repro.yml`, then replays the command and
returns one deterministic verdict:

- `REPRODUCED`
- `NOT_REPRODUCED`
- `ENVIRONMENT_BLOCKED`

The verdict engine does not depend on an LLM.

## Install

Install the v0.1.0 release wheel:

```bash
python -m pip install https://github.com/taopeng9192/crossrepro/releases/download/v0.1.0/crossrepro-0.1.0-py3-none-any.whl
crossrepro --help
```

The release is validated on GitHub-hosted Windows, Ubuntu and macOS runners
with Python 3.10 and 3.12. See `VALIDATION_REPORT.md` and the linked workflow
for the exact evidence boundary.

## Development install

```bash
python -m venv .venv
# activate the venv
python -m pip install -e ".[dev]"
crossrepro --help
pytest
```

## CLI

Capture an exact shell command (recommended when quoting/globbing matters):

```bash
crossrepro collect --command-text "python failing.py"
```

Replay a spec from the repository root:

```bash
crossrepro replay .crossrepro/latest/repro.yml --base-dir . --report report.json
```

Pack sanitized evidence:

```bash
crossrepro pack
```

Generate a GitHub Actions workflow:

```bash
crossrepro ci .crossrepro/latest/repro.yml
```

The generated workflow installs CrossRepro from the checked-out repository by
default (`--install-source .`). For another project's repository, specify an
available CrossRepro wheel or published package requirement with
`--install-source`; v0.1.0 is distributed through the GitHub release wheel, not
claimed to be on PyPI.

To run the three examples plus the capture/replay/bundle checks locally:

```bash
python scripts/validate_examples.py --output .validation/local
```

Use a new output directory for each evidence run; existing ZIPs are not overwritten.

## Why `--command-text` exists

When a shell expands wildcards before CrossRepro starts, the original shell
syntax is already lost. Use `--command-text` when exact quoting, wildcard, or
PowerShell/Bash semantics are part of the bug.

Argument mode preserves literal arguments for PowerShell and POSIX shells.
PowerShell commands propagate the last native command's exit code; pure
PowerShell errors return 1, and an explicit `exit` takes precedence. For compound
scripts, use an explicit exit policy when intermediate failures should be ignored.

## Privacy model

CrossRepro is minimization-first:

1. collect only a small allowlist of environment metadata;
2. redact stored command/stdout/stderr;
3. refuse to pack raw evidence files or detected high-risk secrets.

Bundles contain UTF-8 text evidence, not arbitrary binary attachments or linked
files. A bundle does not include the source checkout automatically. Recipients
must obtain the relevant source and dependencies separately. Replay executes the
authored commands with the current user's permissions; it is not a sandbox.

See `docs/privacy.md`.

## Troubleshooting

See `docs/troubleshooting.md` for common local setup, replay and validation
failures. The report emitted by `replay` is sanitized, but still inspect an
artifact before sharing it.

## Reproduction protocol

See `docs/repro-schema.md`.

## Current validation boundary

See `VALIDATION_REPORT.md` for exactly what was verified locally and in hosted
GitHub Actions.
