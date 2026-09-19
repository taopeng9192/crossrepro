# CrossRepro — turn a failing test into a verified repair

[![Test](https://github.com/taopeng9192/crossrepro/actions/workflows/test.yml/badge.svg)](https://github.com/taopeng9192/crossrepro/actions/workflows/test.yml)

CrossRepro repairs a target repository from a failing command. Its repair agent
proposes a narrow unified diff; CrossRepro validates that diff and reruns the
same command. It reports `FIXED` only when the command failed before the change
and passes after it.

Use it when a CLI command, build, test, or script fails and you need a
reviewable, test-verified candidate fix rather than a screenshot or a guess.

> **中文简介：** CrossRepro 用失败测试驱动修复：agent 只生成统一 diff，程序校验补丁、重跑原测试，并且只有测试从失败变为通过才输出 `FIXED`。复现和证据打包仍可用于定位问题，但产品目标是修复代码。

## The problem it solves

A reliable repair needs more than “ask a model to change code”. It must know
which test is broken, make a minimal patch, and prove that the exact test now
passes. Otherwise a patch is only an unverified suggestion.

CrossRepro provides that workflow:

```text
failing command
  → fix: run and confirm the baseline failure
  → agent: return one constrained unified diff
  → CrossRepro: validate and apply the diff
  → fix: rerun the same command
  → FIXED only if the command now passes; otherwise revert the patch
```

## What it can repair — and when to use it

CrossRepro is for a **locally reproducible code defect**: a command currently
fails, the expected outcome is that it passes, and a small change to existing
text source may solve it. Typical examples include:

| Problem you can reproduce | Examples of a repair it can propose |
|---|---|
| A unit or integration test fails | An incorrect condition, missing branch, wrong return value, or off-by-one error |
| Input handling rejects valid data or accepts invalid data | A parsing, validation, escaping, or serialization correction |
| Code raises an exception on a known path | A wrong import, function call, type conversion, null check, or error-handling path |
| A command behaves differently on one supported platform | A platform-specific path, quoting, or configuration-read fix, if the command reproduces locally |
| A regression has a focused test | A minimal change in the source file covered by that test |

Use it when all of these are true:

1. You can supply one command that fails now and should pass after the repair.
2. The target repository and its test dependencies are already runnable on your machine.
3. You can identify the relevant source files, preferably with `--include`.
4. You are authorized to send the selected source and sanitized failure output to the chosen provider.
5. You will review the resulting diff before committing it. `FIXED` proves the supplied command passed; it does not prove every behavior in the application is correct.

It is not the right tool for an outage caused only by a remote service, missing
credentials, an unavailable database, an unknown expected behavior, a flaky
test, or a change that needs new files, dependency upgrades, migrations, or a
large redesign. In those cases, first make the failure deterministic and decide
the expected behavior; then use CrossRepro for a focused source-level repair.

> **中文说明：** 它适合“本机能稳定复现、知道应当通过、通常可用少量现有源码修改解决”的问题，例如测试断言失败、边界条件错误、参数校验、解析/序列化、空值或类型处理、错误的调用与跨平台路径问题。它不适合直接修复线上服务故障、缺少密钥或数据库、没有明确预期、测试不稳定、需要大规模重构或新增依赖的情况。

## How it differs from a general coding agent

CrossRepro does not claim that its repair model is better than every coding
agent. Its value is the **verification boundary around the model**:

| General chat or autonomous coding agent | CrossRepro |
|---|---|
| May edit files directly and report a plausible answer | Receives a bounded source context and can return only one unified diff |
| May decide which commands to run | CrossRepro runs only the failing command that you supplied |
| A suggested patch may never be tested | It records the baseline failure, reruns the same command, and emits `FIXED` only after that command passes |
| A failed attempt can leave changes behind | Failed verification restores the original target files |
| Often needs a separate API setup | The default provider uses an already ChatGPT-authenticated local Codex CLI; the OpenAI API is optional |

It also keeps the earlier reproduction workflow: when the failure is not yet
clear enough to repair, you can capture, redact, replay, bundle, and run the
same reproduction in CI. That gives a maintainer evidence to investigate
instead of only a copied error message.

The legacy reproduction commands remain useful for examples such as:

- `npm test` fails on Windows but succeeds in CI;
- a Python script fails only on one developer machine;
- PowerShell and Bash interpret the same command differently;
- an open-source issue needs a small, verifiable reproduction package.

## Repair a project

The default provider uses a locally installed, ChatGPT-logged-in Codex CLI, so
it does not require an API key. Confirm that login first:

```powershell
codex login status
```

Then run a known failing test from any target repository. Start without
`--apply`: this writes a candidate patch and report, but leaves the target
source unchanged.

```powershell
crossrepro fix --repo C:\source\target-project --test "python -m pytest tests/test_login.py" --provider codex --include src\login.py
```

Review `.crossrepro/fix/candidate.patch`. To apply that exact candidate and
retain it only when the test passes, validate it with `--patch-file --apply`:

```powershell
crossrepro fix --repo C:\source\target-project --test "python -m pytest tests/test_login.py" --patch-file C:\source\target-project\.crossrepro\fix\candidate.patch --include src\login.py --apply
```

`--include` is optional. When omitted, CrossRepro selects supported UTF-8 source
files, skips common dependency/build directories and `.env` files, and limits
the project context to 90 KB. The selected source and sanitized test output are
sent to the selected agent service. Do not use either provider for source code
you are not authorized to share.

To use the OpenAI API instead, install the optional dependency and select the
provider explicitly:

```powershell
python -m pip install -e ".[agent]"
$env:OPENAI_API_KEY = "<your API key>"
crossrepro fix --repo C:\source\target-project --test "python -m pytest tests/test_login.py" --provider openai --model <model-id> --include src\login.py
```

| Repair status | Meaning |
|---|---|
| `FIXED` | The supplied test failed before the patch and passed after it. The change remains in the target repository. |
| `CANDIDATE` | A valid patch was saved, but `--apply` was not used. Target source is unchanged. |
| `BASELINE_PASSED` | The supplied command already passed, or did not complete with a usable failure. No patch was requested. |
| `PATCH_REJECTED` | The provider returned a malformed, unsafe, stale, or unsupported diff. Target source is unchanged. |
| `VERIFICATION_FAILED` | The patch was applied but the supplied test still failed; CrossRepro reverted the patch. |
| `PROVIDER_ERROR` | The API key, optional dependency, or provider response was unavailable or invalid. |

CrossRepro never commits, pushes, upgrades dependencies, or runs commands chosen
by the provider. The provider can only return a diff for existing UTF-8 source
files; CrossRepro runs only the `--test` command supplied by you.

## Reproduce a problem when a fix needs better evidence

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

- Repair quality depends on the failing command. A command that does not cover
  the bug cannot prove that the repair is correct.
- `--apply` writes the provider's candidate change to the target repository
  temporarily. CrossRepro reverts it if the supplied test fails, but you should
  still inspect a verified diff before committing it.
- It is not a sandbox: replay executes the authored commands with your current
  user permissions. Inspect commands from an untrusted package before running them.
- The default Codex provider requires an already authenticated local Codex CLI.
  It runs in an ephemeral, read-only workspace and returns a patch only. The
  optional OpenAI provider requires an API key.
- It records a small allowlist of environment metadata, rather than dumping the
  full process environment. It redacts common keys, cookies, authorization
  headers, private keys, emails, and user-home paths; see the
  [privacy rules](docs/privacy.md).
- It is not malware analysis, DLP, or a replacement for an isolated execution
  environment.

## 中文快速上手

1. 安装 Python 3.10+，从本仓库安装后先执行 `codex login status` 确认本机 Codex 已通过 ChatGPT 登录。
2. 先生成候选修复（不修改目标源码）：

   ```powershell
   crossrepro fix --repo C:\目标项目 --test "python -m pytest tests/test_login.py" --provider codex --include src\login.py
   ```

3. 查看 `.crossrepro/fix/candidate.patch`；确认后用 `--patch-file <该补丁> --apply` 验证同一份补丁。只有原测试由失败变通过时，补丁才会保留，并显示 `FIXED`。
4. 如需把问题交给他人复查，再使用以下复现流程：

   ```powershell
   crossrepro collect --command-text "<原始失败命令>" --out .crossrepro/demo
   ```

5. 编辑 `.crossrepro/demo/repro.yml`，补充“出现什么错误、退出码或文件状态才算问题仍存在”。
6. 执行 `crossrepro replay ... --report report.json` 查看三种结果：
   `REPRODUCED` 为已复现，`NOT_REPRODUCED` 为未复现，`ENVIRONMENT_BLOCKED` 为环境未准备好。
7. 执行 `crossrepro pack` 生成分享包。包里没有项目源码和依赖，接收方需要自行准备。

## More documentation

- [Reproduction protocol](docs/repro-schema.md)
- [Privacy and bundle rules](docs/privacy.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture](docs/architecture.md)
- [Validation evidence and scope](VALIDATION_REPORT.md)
