# Changelog

## Unreleased

- Add `crossrepro fix`, a test-constrained repair flow. It establishes a
  baseline failure, accepts one provider-generated unified diff, applies it
  only with `--apply`, reruns the supplied test, and reverts an unsuccessful
  verification.
- Add an optional OpenAI Responses API provider (`crossrepro[agent]`). It can
  return a patch but has no shell or filesystem tool access.

- Check Windows Python app aliases with a bounded startup probe so an unavailable
  Store placeholder produces `ENVIRONMENT_BLOCKED`. Preserve working Python
  aliases and discovery of unrelated application aliases.
- Make example integration tests explicitly use their test interpreter.

## 0.1.1 — 2026-09-18

### Timeout cleanup

- Bound Windows `taskkill` and post-timeout output draining so a detached child
  that retains inherited capture pipes cannot make `collect` wait forever.
- Return sanitized timeout evidence for manual review when residual pipe readers
  cannot finish, and cover that path with unit tests.

### Real OSS validation record

- Record the first isolated evaluation of a public upstream CLI issue in
  `docs/cases/case-001-agent-browser-1407.md`. It is an observed timeout, not
  an upstream maintainer confirmation or a deterministic replay verdict.

## 0.1.0 — 2026-09-18

### Release validation

- Publish the independent public repository and validate the complete matrix on
  GitHub-hosted Windows, Ubuntu and macOS runners with Python 3.10 and 3.12.
- Inspect all six uploaded evidence bundles: 112 tests per job with zero
  failures/errors; platform-specific shell-glob verdicts; bundle privacy scan,
  SHA-256 verification, wheel build and clean installation all pass.

### 0.1.0.dev2 — release-readiness follow-up (2026-09-18)

- Make the clean-wheel CI check select the sole built CrossRepro wheel instead
  of hard-coding a development version in the workflow.
- Reject reuse of a non-empty example-validation output directory so evidence
  from different runs cannot be silently mixed.
- Adopt current setuptools license metadata, add operational troubleshooting,
  and record the MIT licenses of research sources without claiming their code
  was copied into CrossRepro.

### 0.1.0.dev1 — local review fixes (2026-09-18)

- Preserve PowerShell native exit codes and literal argument quoting; capture
  output as bytes and clean up owned command trees on timeout.
- Redact complete reports and structured metadata; add Cookie/Authorization
  coverage and compare signatures before redaction without persisting raw data.
- Scan every included bundle file, reject unscannable content and links,
  validate repro specs and build manifest/checksums from the scanned snapshot.
- Preserve unknown files during repeated capture; reject unsafe Windows paths,
  misspelled schema fields and boolean versions; parse Git status without
  losing leading spaces or renamed filenames.
- Generate CI with data-only path arguments, explicit installation source,
  per-job summary and required report artifact. Add actual example/bundle and
  clean wheel installation checks to the three-platform test matrix.
- Release remains gated on hosted Windows/Linux/macOS validation.

### 0.1.0.dev0 — original delivery

- Initial CrossRepro development baseline.
- Deterministic command capture and redaction.
- `repro.yml` v1 loader and validator.
- Replay and three-state verdict engine.
- Portable bundle with manifest and SHA-256 checksums.
- GitHub Actions workflow generator.
