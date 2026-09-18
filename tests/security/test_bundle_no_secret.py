from pathlib import Path
import zipfile

from crossrepro.bundle.builder import build_bundle
from crossrepro.redact.engine import redact_text


def test_sanitized_fake_secret_never_appears_in_zip(tmp_path: Path):
    secret = "TEST_ONLY_SECRET_123456"
    source = tmp_path / "bundle"
    source.mkdir()
    sanitized = redact_text(f"api_key={secret}\nuser=test@example.com\n").text
    (source / "repro.yml").write_text("version: 1\nname: bundle-test\ncommand: {run: 'echo ok'}\nbug_signature: {exit_code: {equals: 1}}\n", encoding="utf-8")
    (source / "stderr.txt").write_text(sanitized, encoding="utf-8")
    out = tmp_path / "bundle.zip"
    build_bundle(source, out)
    with zipfile.ZipFile(out) as archive:
        joined = b"\n".join(archive.read(name) for name in archive.namelist())
    assert secret.encode() not in joined
    assert b"test@example.com" not in joined
