# `repro.yml` v1

CrossRepro v1 describes how to execute a reproduction and which observable
conditions mean the target bug was reproduced.

```yaml
version: 1
name: example
workdir: examples/example

setup:
  commands:
    - python make_fixture.py

command:
  default:
    shell: bash
    run: "python check.py"
  windows:
    shell: pwsh
    run: "python check.py"

bug_signature:
  exit_code:
    equals: 2
  stderr:
    contains:
      - "known failure marker"

requirements:
  commands:
    - python

platforms:
  - windows-latest
  - ubuntu-latest
  - macos-latest
```

## Semantics

- `workdir` is relative to the replay `--base-dir` and may not be absolute or
  contain `..`.
- platform commands override `command.default`.
- all configured bug-signature checks use AND semantics.
- substring checks operate on original in-memory command output, before
  redaction. Report check names use 1-based indexes to avoid copying secrets
  from signatures into reports.
- a completed execution that fails one or more signature checks is
  `NOT_REPRODUCED`.
- missing requirements, missing shell, setup failure, invalid workdir or timeout
  produce `ENVIRONMENT_BLOCKED`.
- `REPRODUCED` is a valid experiment result, not an infrastructure error.

## Fields and compatibility

| Field | Required / default | Meaning |
|---|---|---|
| `version` | Required integer `1` | Booleans and unknown versions are rejected. |
| `name` | Required nonempty string | Reproduction identifier. |
| `workdir` | `.` | Relative to `--base-dir`; no drive, rooted path, traversal or alternate data stream. |
| `command` | Required | `default: {run, shell?}` plus optional `windows`, `linux`, `macos` overrides. Flat `{run, shell?}` is also accepted. |
| `setup.commands` | `[]` | Commands run in order before the target. |
| `requirements.commands` | `[]` | Executables that must be discoverable on PATH before setup. |
| `bug_signature` | Required, nonempty | All exit, stream and file checks must pass. |
| `platforms` | Three default runners when omitted/empty | Generated CI targets: Windows, Ubuntu and macOS latest runners. |
| `capture` | Omitted | Optional `stdout`, `stderr`, `environment`, `git` flags; v1 supports only `true`. |
| `redaction` | Always enabled | Optional `{enabled: true}`; disabling is unsupported. |

Supported shells: `bash`, `sh`, `zsh`, `pwsh`, `powershell`, `cmd`, `cmd.exe`.
When omitted, Windows prefers PowerShell and Unix prefers Bash. Unknown fields
are rejected rather than silently weakening a signature. Empty substring checks
are invalid. Relative file signatures must also resolve inside the workdir;
links escaping that boundary produce `ENVIRONMENT_BLOCKED`.

v1 remains a pre-release protocol. Any incompatible field or semantic change
after release requires a new protocol version; development snapshot differences
are recorded in `CHANGELOG.md`.

## Execution/report contract

PowerShell execution preserves the last native exit status. Explicit `exit N`
overrides it. A pure PowerShell failure without a native exit status returns 1.
Stdout/stderr are captured as bytes, decoded as UTF-8 when valid, otherwise the
host locale encoding, with replacement only for undecodable bytes. This avoids
reader-thread crashes but does not preserve arbitrary binary output losslessly.
Timeout cleanup targets only the process tree created for the command.

Reports use `{schema_version, repro, execution, result}`. Execution includes
platform, shell, command, exit_code, sanitized streams, workdir, timeout and
blocked reason. Result contains verdict, boolean checks and blocked reason.
All three verdicts are successful CLI experiment outcomes (exit 0); invalid
specifications or tool failures produce a nonzero CLI status.

## Supported v1 signatures

- exact exit code
- non-zero exit code
- stdout substring
- stderr substring
- relative file exists
- relative file missing
