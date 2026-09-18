from pathlib import Path

import pytest

from crossrepro.schema.loader import ReproLoadError, load_repro
from crossrepro.schema.validator import InvalidReproSpec, validate_repro


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "repro.yml"
    path.write_text(text.strip(), encoding="utf-8")
    return path


def test_valid_repro(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: example
workdir: .
command:
  default:
    shell: bash
    run: "python test.py"
bug_signature:
  exit_code:
    equals: 2
platforms:
  - windows-latest
  - ubuntu-latest
  - macos-latest
""")
    spec = load_repro(path)
    validate_repro(spec)
    assert spec.name == "example"
    assert spec.workdir == "."


def test_flat_command_form_is_supported(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: example
command:
  run: "python test.py"
bug_signature:
  exit_code:
    mode: nonzero
""")
    spec = load_repro(path)
    validate_repro(spec)
    assert spec.default_command.run == "python test.py"


def test_empty_signature_fails(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: bad
command:
  run: "python test.py"
bug_signature: {}
""")
    spec = load_repro(path)
    with pytest.raises(InvalidReproSpec, match="bug_signature"):
        validate_repro(spec)


def test_workdir_cannot_escape(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: bad
workdir: ../outside
command:
  run: "python test.py"
bug_signature:
  exit_code:
    equals: 1
""")
    spec = load_repro(path)
    with pytest.raises(InvalidReproSpec, match="workdir"):
        validate_repro(spec)


def test_file_signature_cannot_escape(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: bad
command:
  run: "python test.py"
bug_signature:
  files:
    exists:
      - ../secret.txt
""")
    spec = load_repro(path)
    with pytest.raises(InvalidReproSpec, match="stay inside"):
        validate_repro(spec)


def test_bad_list_type_has_readable_error(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: bad
command:
  run: "python test.py"
bug_signature:
  stderr:
    contains: nope
""")
    with pytest.raises(ReproLoadError, match="list of strings"):
        load_repro(path)


def test_unknown_command_key_fails(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: bad
command:
  run: "python test.py"
  solaris:
    run: "x"
bug_signature:
  exit_code:
    equals: 1
""")
    with pytest.raises(ReproLoadError, match="unsupported command key"):
        load_repro(path)


@pytest.mark.parametrize("fragment, expected", [
    ("version: 2", "version must be 1"),
    ("name: ''", "name must be non-empty"),
])
def test_basic_validation_errors(tmp_path: Path, fragment: str, expected: str):
    base = """
version: 1
name: ok
command:
  run: "python x.py"
bug_signature:
  exit_code:
    equals: 1
"""
    if fragment.startswith("version"):
        base = base.replace("version: 1", fragment)
    else:
        base = base.replace("name: ok", fragment)
    spec = load_repro(write(tmp_path, base))
    with pytest.raises(InvalidReproSpec, match=expected):
        validate_repro(spec)


def test_invalid_shell_and_duplicate_runner(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: bad
command:
  default:
    shell: fish
    run: "x"
bug_signature:
  exit_code:
    equals: 1
platforms:
  - ubuntu-latest
  - ubuntu-latest
""")
    spec = load_repro(path)
    with pytest.raises(InvalidReproSpec) as exc:
        validate_repro(spec)
    assert "unsupported shell" in str(exc.value)
    assert "duplicates" in str(exc.value)


def test_invalid_exit_mode_and_both_equals_mode(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: bad
command:
  run: "x"
bug_signature:
  exit_code:
    equals: 1
    mode: zero
""")
    spec = load_repro(path)
    with pytest.raises(InvalidReproSpec) as exc:
        validate_repro(spec)
    assert "mode must be 'nonzero'" in str(exc.value)
    assert "cannot define both" in str(exc.value)


def test_empty_setup_and_requirement_names_fail(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: bad
setup:
  commands: [""]
requirements:
  commands: [" " ]
command:
  run: "x"
bug_signature:
  exit_code:
    equals: 1
""")
    spec = load_repro(path)
    with pytest.raises(InvalidReproSpec) as exc:
        validate_repro(spec)
    assert "setup.commands" in str(exc.value)
    assert "requirements.commands" in str(exc.value)


def test_unknown_runner_fails(tmp_path: Path):
    path = write(tmp_path, """
version: 1
name: bad
command:
  run: "x"
bug_signature:
  exit_code:
    equals: 1
platforms: [solaris-latest]
""")
    spec = load_repro(path)
    with pytest.raises(InvalidReproSpec, match="unsupported GitHub runner"):
        validate_repro(spec)
