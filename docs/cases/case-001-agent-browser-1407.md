# Case 001: agent-browser Windows output-capture timeout

## Upstream context

- Upstream repository: https://github.com/vercel-labs/agent-browser
- Public issue: https://github.com/vercel-labs/agent-browser/issues/1407
- Upstream state observed on 2026-09-18: open.

The upstream report describes a Windows PowerShell output-capture hang after an
`open`, `close`, `open` sequence. It identifies `agent-browser` 0.27.0 as an
affected version. This case independently evaluates that sequence; it does not
claim an upstream diagnosis or maintainer endorsement.

## Local evaluation

- Host: Windows 10, PowerShell.
- Target package: `agent-browser@0.27.0`, invoked through `npm exec` with an
  npm cache under `F:\Codex\cache`.
- Browser state: isolated `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, and
  named `crossrepro-case001` session so existing browser automation state was
  not reused.
- Sequence: `open https://example.com`, `close`, then a second `open` while
  CrossRepro captured PowerShell stdout/stderr.
- Capture timeout: 20 seconds.

The command did not complete within the configured timeout. CrossRepro wrote
sanitized evidence with `timed_out: true` in 24,640 ms, then the named test
session was closed. The redaction report recorded zero matches and zero
high-risk matches. Local evidence is retained under
`.validation/oss-case-001-raw7/` and is intentionally not published as a
portable reproduction artifact because v1 does not express a timeout as a
deterministic `bug_signature`.

## Result boundary

This is an **observed timeout in an isolated local evaluation**. It is not yet:

- a three-platform result;
- a `REPRODUCED` replay verdict under the v1 schema;
- an upstream issue comment, PR, or maintainer feedback.

The run exposed a CrossRepro timeout-cleanup defect: a detached process could
retain capture pipes and make collection wait indefinitely. Version 0.1.1
limits Windows process-tree termination and post-timeout draining so it returns
the manual-review evidence instead.
