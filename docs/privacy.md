# Privacy and redaction model

CrossRepro uses a minimization-first approach.

## Collection

The environment collector records a small allowlist of metadata and selected
runtime versions. It does not dump the full process environment.

## Redaction

Stored command, stdout and stderr are scanned for common developer-log secrets
and PII such as bearer tokens, JWTs, private keys, credential URLs and email
addresses.

Cookie/Set-Cookie and non-Bearer Authorization headers are also covered.
Structured metadata and reports are redacted before JSON serialization,
including command text, setup failures, path values and report names. Bug
signatures compare the original streams in memory; reports contain sanitized
streams and numbered checks, never the raw signature substrings.

## Fail closed during pack

`crossrepro pack` refuses to create a bundle when:

- a file is named `raw_*`;
- a path is inside a `raw_*` directory;
- a supported high-risk secret pattern still exists in any included file;
- content is not UTF-8 text or contains NUL bytes;
- a source entry is a symbolic link or Windows reparse point;
- a filename contains detected sensitive data;
- `repro.yml` does not pass the v1 loader and validator.

Every included file is scanned regardless of extension. Scanned bytes are kept
as one snapshot and used to construct the manifest, checksums and ZIP, so later
ordinary source changes do not change the already-scanned artifact. Generated
manifest/checksum files are rebuilt in memory; pack does not modify its source.
Existing output files are refused. Do not mutate a source directory concurrently
with capture or pack; this CLI does not provide filesystem transaction isolation.

Repeated capture may replace only recognized files in a directory with the exact
CrossRepro marker. Unknown files, links and current/ancestor working directories
are refused instead of recursively deleting the directory.

Pattern-based redaction can never guarantee discovery of every possible secret.
Users must still review a bundle before public upload.

The scanner is neither malware isolation nor a general binary/DLP scanner.
Reproduction commands execute locally with the caller's permissions.
