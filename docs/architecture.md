# Architecture

```text
failing test -> repair provider -> validated unified diff -> test verification -> FIXED/revert
                                      \
collect -> sanitize -> repro.yml -> replay -> verdict -> bundle/CI
```

Module boundaries are intentionally strict:

- `capture`: execution and minimal environment/Git metadata
- `redact`: deterministic text redaction
- `schema`: load/validate portable reproduction descriptions
- `replay`: execute setup and target command
- `verdict`: compare execution to a bug signature
- `bundle`: manifest/checksum/archive
- `ci`: generate GitHub Actions workflow
- `repair`: assemble bounded source context, ask a provider for a unified diff,
  validate/apply that diff, rerun the user-supplied test, and revert a failed
  verification
- `cli`: orchestration only

The core has no web server, database, Docker dependency, MCP server, or local
model. The default provider invokes an authenticated local Codex CLI in an
ephemeral read-only sandbox. The optional `agent` extra supplies the OpenAI
Responses API adapter. Both providers can return a patch only; they do not
receive CrossRepro shell or filesystem tools.
