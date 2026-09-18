from pathlib import Path
import json
import zipfile

import pytest

from crossrepro.bundle.builder import UnsafeBundleError, build_bundle
from crossrepro.bundle.hashing import sha256_file


def test_hash_is_deterministic(tmp_path: Path):
    path = tmp_path / "x.txt"
    path.write_text("hello", encoding="utf-8")
    assert sha256_file(path) == sha256_file(path)


def test_bundle_contains_manifest_and_checksums(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text("version: 1\nname: bundle-test\ncommand: {run: 'echo ok'}\nbug_signature: {exit_code: {equals: 1}}\n", encoding="utf-8")
    out = tmp_path / "bundle.zip"
    build_bundle(source, out)
    assert out.exists()
    with zipfile.ZipFile(out) as archive:
        names = set(archive.namelist())
        assert {"repro.yml", "manifest.json", "SHA256SUMS"} <= names
        manifest = json.loads(archive.read("manifest.json"))
        assert any(item["path"] == "repro.yml" for item in manifest["files"])


def test_raw_file_refuses_pack(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text("version: 1\nname: bundle-test\ncommand: {run: 'echo ok'}\nbug_signature: {exit_code: {equals: 1}}\n", encoding="utf-8")
    (source / "raw_stdout.txt").write_text("safe", encoding="utf-8")
    with pytest.raises(UnsafeBundleError, match="raw evidence"):
        build_bundle(source, tmp_path / "x.zip")


def test_high_risk_secret_refuses_pack(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text("version: 1\nname: bundle-test\ncommand: {run: 'echo ok'}\nbug_signature: {exit_code: {equals: 1}}\n", encoding="utf-8")
    (source / "stderr.txt").write_text("Bearer abcdefghijklmnop", encoding="utf-8")
    with pytest.raises(UnsafeBundleError, match="high-risk"):
        build_bundle(source, tmp_path / "x.zip")


def test_bundle_output_cannot_be_inside_source(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text("version: 1\nname: bundle-test\ncommand: {run: 'echo ok'}\nbug_signature: {exit_code: {equals: 1}}\n", encoding="utf-8")
    (source / "safe.txt").write_text("safe", encoding="utf-8")
    with pytest.raises(ValueError, match="outside the source"):
        build_bundle(source, source / "bundle.zip")


def test_bundle_requires_repro_yml(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "safe.txt").write_text("safe", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain repro.yml"):
        build_bundle(source, tmp_path / "x.zip")


def test_internal_state_marker_is_not_bundled(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "repro.yml").write_text("version: 1\nname: bundle-test\ncommand: {run: 'echo ok'}\nbug_signature: {exit_code: {equals: 1}}\n", encoding="utf-8")
    (source / ".crossrepro-state").write_text("internal", encoding="utf-8")
    out = tmp_path / "x.zip"
    build_bundle(source, out)
    with zipfile.ZipFile(out) as archive:
        assert ".crossrepro-state" not in archive.namelist()
        assert ".crossrepro-state" not in archive.read("SHA256SUMS").decode()
