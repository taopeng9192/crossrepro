# Changelog

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
