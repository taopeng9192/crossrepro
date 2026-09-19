# Troubleshooting

## `python` or `crossrepro` cannot be found

Create and activate the project virtual environment, then install the project:

```text
python -m venv .venv
python -m pip install -e ".[dev]"
python -m crossrepro.cli --help
```

Use `python -m crossrepro.cli` while diagnosing PATH issues. It executes the
module with the Python interpreter you selected and does not depend on the
console-script lookup.

## Replay reports `ENVIRONMENT_BLOCKED`

The target command could not start in the current environment. Check the
sanitized `execution` and `result` fields in the report, then install or select
the required runtime, shell or project dependency before replaying. This verdict
does not establish whether the underlying bug reproduces.

On Windows, an App Installer `python.exe` alias may be discoverable even when
it cannot start Python. CrossRepro probes Python app aliases with a five-second
limit and reports `ENVIRONMENT_BLOCKED` if startup fails. Working Python app
aliases remain supported. Activate your virtual environment or select a working
Python on PATH before replaying. CrossRepro does not modify the system PATH.

## A shell command returns an unexpected code

Use `collect --command-text` when the original quoting, wildcard expansion or
shell syntax matters. On PowerShell, CrossRepro preserves the final native
command's exit code; an explicit `exit` in the command takes precedence. Add an
explicit exit policy to compound scripts when an intermediate failure is meant
to be ignored.

## `pack` refuses a file

Bundles only contain UTF-8 text evidence and reject symbolic links, binary
content, raw evidence files and detected high-risk secrets. Remove the unsafe
material from the capture directory, or keep it outside the portable bundle and
share it only through an approved channel.

## Example validation refuses the output directory

`scripts/validate_examples.py` requires a new or empty output directory so that
reports, ZIP files and checksums all come from one run. Choose a new path, for
example `.validation/windows-rerun`, rather than deleting existing evidence.

## Clean-wheel validation fails before the project is installed

The wheel check creates a temporary virtual environment and installs the built
wheel with its declared dependencies. Check the command output for an unavailable
Python package index, proxy, certificate or runtime dependency; no report is a
passing clean-install check. Use `--wheel-dir dist` only when that directory
contains exactly one `crossrepro-*.whl` file.
