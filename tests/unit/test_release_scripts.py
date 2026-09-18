"""Regression checks for release-validation helpers."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[2]


def load_script(name: str):
    specification = spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert specification and specification.loader
    module = module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_find_wheel_selects_sole_crossrepro_wheel(tmp_path: Path):
    script = load_script("validate_wheel")
    expected = tmp_path / "crossrepro-0.1.0.dev2-py3-none-any.whl"
    expected.touch()
    (tmp_path / "unrelated-1.0.0-py3-none-any.whl").touch()

    assert script.find_wheel(tmp_path) == expected


def test_find_wheel_rejects_missing_or_ambiguous_builds(tmp_path: Path):
    script = load_script("validate_wheel")
    with pytest.raises(FileNotFoundError, match="no CrossRepro wheel"):
        script.find_wheel(tmp_path)

    (tmp_path / "crossrepro-0.1.0.dev1-py3-none-any.whl").touch()
    (tmp_path / "crossrepro-0.1.0.dev2-py3-none-any.whl").touch()
    with pytest.raises(ValueError, match="expected one CrossRepro wheel"):
        script.find_wheel(tmp_path)


def test_example_validation_refuses_nonempty_output(tmp_path: Path):
    script = load_script("validate_examples")
    output = tmp_path / "evidence"
    output.mkdir()
    (output / "old-report.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="new or empty"):
        script.validate(tmp_path, output)
