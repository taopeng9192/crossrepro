# Architecture

```text
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
- `cli`: orchestration only

The v0.1 core has no web server, database, Docker dependency, MCP server or LLM
dependency.
