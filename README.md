# CrossRepro — turn “it fails on my machine” into a reproducible bug report

[![Test](https://github.com/taopeng9192/crossrepro/actions/workflows/test.yml/badge.svg)](https://github.com/taopeng9192/crossrepro/actions/workflows/test.yml)

CrossRepro captures a failing command, removes common sensitive data from the
evidence, describes the expected failure in `repro.yml`, and replays it on
another machine. It gives a deterministic answer instead of asking someone to
guess from a screenshot or a long chat log.

Use it when a CLI command, build, test, or script fails for you but cannot be
reproduced by a teammate, a project maintainer, or CI.

> **中文简介：** CrossRepro 用来把“我电脑上报错”变成别人可以验证的复现材料：记录失败命令、脱敏日志和最小环境信息，生成 `repro.yml`，然后在另一环境重放并给出明确结果。它不修复目标程序，也不是沙箱。

## The problem it solves

A useful bug report needs more than “command X failed”. The recipient needs to
know which command ran, which working directory and tools it used, what output
proves the problem, and whether their result is comparable to yours.

CrossRepro provides that workflow:

```text
failing command
  → collect: save sanitized evidence and create a repro.yml draft
  → edit repro.yml: define what counts as the bug
  → replay: run it in the target environment and evaluate the result
  → pack: create a shareable evidence bundle with checksums
```

It is useful for examples such as:

- `npm test` fails on Windows but succeeds in CI;
- a Python script fails only on one developer machine;
- PowerShell and Bash interpret the same command differently;
- an open-source issue needs a small, verifiable reproduction package.

## Understand the result first

`replay` produces one of these business results:

| Result | Meaning | What to do next |
|---|---|---|
| `REPRODUCED` | The command ran and met every failure condition in `repro.yml`. | The issue is present in this environment. |
| `NOT_REPRODUCED` | The command ran, but did not meet the failure conditions. | Compare code, versions, dependencies, and environment. It may be fixed. |
| `ENVIRONMENT_BLOCKED` | A required command, shell, directory, or dependency is unavailable, or execution timed out. | Fix the environment first. This does **not** say whether the bug is fixed. |

These are experiment outcomes, so `replay` itself exits with code `0` for all
three. Read the terminal result or the JSON file written with `--report`; do
not use the process exit code as the verdict.

## Install the current version from this repository

You need Python 3.10 or newer. Use PowerShell on Windows, or a terminal on
macOS/Linux.

```powershell
git clone https://github.com/taopeng9192/crossrepro.git
cd crossrepro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
crossrepro --help
```

If PowerShell cannot activate the virtual environment, call its Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m crossrepro.cli --help
```

On macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -e .
crossrepro --help
```

Install from `main` for the current code. The GitHub v0.1.1 release wheel is an
older published package and does not contain changes committed to `main` later.

## A complete reproduction in five minutes

Assume `failing.py` is in the current directory and `python failing.py` exits
with a nonzero code.

### 1. Capture the failure

```powershell
crossrepro collect --command-text "python failing.py" --out .crossrepro/demo
```

This creates a directory like:

```text
repro.yml                 editable reproduction definition
command.json              command, exit code, and timing metadata
evidence/stdout.txt       sanitized standard output
evidence/stderr.txt       sanitized error output
evidence/environment.json minimal environment information
evidence/git.json         current Git revision and working-tree state
```

CrossRepro creates a `repro.yml` draft only when the command fails with a
nonzero exit code and the command text itself contains no detected secret. For
a timeout, a command that exits `0`, or a command containing sensitive data, it
keeps sanitized evidence and asks you to write the reproduction condition
manually.

Prefer `--command-text`: it preserves quoting, wildcards, and PowerShell/Bash
syntax. Passing separate arguments can lose the original shell expression.

### 2. Define what proves the bug

Open `.crossrepro/demo/repro.yml`. The generated draft usually checks the exit
code. Add an error marker or file condition if they are part of the bug:

```yaml
bug_signature:
  exit_code:
    equals: 2
  stderr:
    contains:
      - "expected failure marker"
  files:
    exists:
      - "logs/failed.txt"
```

Every condition must pass to produce `REPRODUCED`. v1 supports an exact or
nonzero exit code, stdout/stderr text, and relative file exists/missing checks.
See the full [repro.yml protocol](docs/repro-schema.md).

### 3. Replay it

```powershell
crossrepro replay .crossrepro/demo/repro.yml --base-dir . --report .crossrepro/demo/report.json
```

`--base-dir` is the target project's source directory. The `workdir` in
`repro.yml` must stay inside that directory. CrossRepro does not download source
code or install the target project's dependencies.

For example, a recipient who has obtained the project source can run:

```powershell
crossrepro replay C:\received\repro\repro.yml --base-dir C:\source\target-project --report C:\received\report.json
```

### 4. Pack the evidence for sharing

```powershell
crossrepro pack --source .crossrepro/demo --output .crossrepro/demo.crossrepro.zip
```

The ZIP contains `repro.yml`, sanitized evidence, a manifest, and
`SHA256SUMS`. Packing rejects raw-evidence directories, links, binary content,
and detected high-risk secrets.

**The ZIP does not include the target project's source code or dependencies.**
The recipient must obtain those separately before running `replay`. Pattern-based
redaction cannot prove that every secret was found, so review a bundle before
uploading it publicly.

## Common commands

```text
crossrepro collect --command-text "<original failing command>" --out <evidence-directory>
crossrepro replay <evidence-directory>/repro.yml --base-dir <target-source-directory> --report <report.json>
crossrepro pack --source <evidence-directory> --output <reproduction.zip>
crossrepro ci <evidence-directory>/repro.yml
```

`ci` generates a GitHub Actions replay workflow for Windows, Ubuntu, and macOS.
You still need to provide the target source, its dependency-installation steps,
and an install source for CrossRepro. The generator does not guess how a project
should build.

## Run the included examples

```powershell
python scripts/validate_examples.py --output .validation/example-run
```

The examples demonstrate:

- `secret-redaction`: a failure reproduces while the fixture API key and email
  are absent from the report and ZIP;
- `missing-runtime`: an unavailable command becomes `ENVIRONMENT_BLOCKED`;
- `shell-glob`: a wildcard can behave differently in Windows PowerShell and a
  Unix shell.

## Safety and limits

- CrossRepro does **not** fix the program you are investigating.
- It is not a sandbox: replay executes the authored commands with your current
  user permissions. Inspect commands from an untrusted package before running them.
- It has no web service, database, Docker requirement, MCP server, or LLM.
  Verdicts come from the checkable conditions in `repro.yml`.
- It records a small allowlist of environment metadata, rather than dumping the
  full process environment. It redacts common keys, cookies, authorization
  headers, private keys, emails, and user-home paths; see the
  [privacy rules](docs/privacy.md).
- It is not malware analysis, DLP, or a replacement for an isolated execution
  environment.

## 中文快速上手

1. 安装 Python 3.10+，按上面的 Windows 或 macOS/Linux 命令从本仓库安装。
2. 在目标项目目录执行：

   ```powershell
   crossrepro collect --command-text "<原始失败命令>" --out .crossrepro/demo
   ```

3. 编辑 `.crossrepro/demo/repro.yml`，补充“出现什么错误、退出码或文件状态才算问题仍存在”。
4. 执行 `crossrepro replay ... --report report.json` 查看三种结果：
   `REPRODUCED` 为已复现，`NOT_REPRODUCED` 为未复现，`ENVIRONMENT_BLOCKED` 为环境未准备好。
5. 执行 `crossrepro pack` 生成分享包。包里没有项目源码和依赖，接收方需要自行准备。

## More documentation

- [Reproduction protocol](docs/repro-schema.md)
- [Privacy and bundle rules](docs/privacy.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture](docs/architecture.md)
- [Validation evidence and scope](VALIDATION_REPORT.md)
