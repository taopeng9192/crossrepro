from __future__ import annotations

from pathlib import Path

import yaml

from .models import BugSignature, CommandSpec, ExitCodeSignature, FileSignature, ReproSpec, StreamSignature


class ReproLoadError(ValueError):
    pass


class ReproYamlLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ReproLoadError("YAML mapping keys must be strings")
            if key in seen:
                raise ReproLoadError("duplicate YAML mapping keys are not allowed")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _as_mapping(value, name: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ReproLoadError(f"{name} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise ReproLoadError(f"{name} keys must be strings")
    return value


def _check_keys(value: dict, allowed: set[str], name: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ReproLoadError(f"unsupported {name} key(s): " + ", ".join(sorted(unknown)))


def _as_string_list(value, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ReproLoadError(f"{name} must be a list of strings")
    return list(value)


def parse_command(raw: dict | None, name: str = "command") -> CommandSpec:
    if not isinstance(raw, dict):
        raise ReproLoadError(f"{name} must be a mapping")
    _as_mapping(raw, name)
    _check_keys(raw, {"run", "shell"}, name)
    run = raw.get("run")
    if not isinstance(run, str) or not run.strip():
        raise ReproLoadError(f"{name}.run must be a non-empty string")
    shell = raw.get("shell")
    if shell is not None and not isinstance(shell, str):
        raise ReproLoadError(f"{name}.shell must be a string")
    return CommandSpec(run=run, shell=shell)


def load_repro(path: Path) -> ReproSpec:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ReproLoadError(f"failed to read repro.yml: {exc}") from exc
    return parse_repro(text)


def parse_repro(text: str) -> ReproSpec:
    try:
        raw = yaml.load(text, Loader=ReproYamlLoader)
    except yaml.YAMLError as exc:
        raise ReproLoadError(f"failed to read YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ReproLoadError("repro.yml root must be a mapping")
    _as_mapping(raw, "repro.yml")
    _check_keys(raw, {"version", "name", "workdir", "setup", "command", "bug_signature", "requirements", "platforms", "capture", "redaction"}, "repro.yml")

    command_raw = _as_mapping(raw.get("command"), "command")
    if not command_raw:
        raise ReproLoadError("command must not be empty")
    allowed_command_keys = {"default", "windows", "linux", "macos", "run", "shell"}
    unknown_command_keys = set(command_raw) - allowed_command_keys
    if unknown_command_keys:
        raise ReproLoadError("unsupported command key(s): " + ", ".join(sorted(unknown_command_keys)))

    if "default" in command_raw:
        if "run" in command_raw or "shell" in command_raw:
            raise ReproLoadError("command must not mix default and flat run/shell forms")
        default_command = parse_command(command_raw["default"], "command.default")
    elif "run" in command_raw:
        default_command = parse_command({key: value for key, value in command_raw.items() if key in {"run", "shell"}}, "command")
    else:
        raise ReproLoadError("command.default is required when command.run is not used")

    platform_commands: dict[str, CommandSpec] = {}
    for key in ("windows", "linux", "macos"):
        if key in command_raw:
            platform_commands[key] = parse_command(command_raw[key], f"command.{key}")

    signature_raw = _as_mapping(raw.get("bug_signature"), "bug_signature")
    _check_keys(signature_raw, {"exit_code", "stdout", "stderr", "files"}, "bug_signature")
    exit_raw = signature_raw.get("exit_code")
    exit_signature = None
    if exit_raw is not None:
        exit_map = _as_mapping(exit_raw, "bug_signature.exit_code")
        _check_keys(exit_map, {"equals", "mode"}, "bug_signature.exit_code")
        exit_signature = ExitCodeSignature(equals=exit_map.get("equals"), mode=exit_map.get("mode"))

    stdout_map = _as_mapping(signature_raw.get("stdout"), "bug_signature.stdout")
    stderr_map = _as_mapping(signature_raw.get("stderr"), "bug_signature.stderr")
    files_map = _as_mapping(signature_raw.get("files"), "bug_signature.files")
    _check_keys(stdout_map, {"contains"}, "bug_signature.stdout")
    _check_keys(stderr_map, {"contains"}, "bug_signature.stderr")
    _check_keys(files_map, {"exists", "missing"}, "bug_signature.files")

    signature = BugSignature(
        exit_code=exit_signature,
        stdout=StreamSignature(_as_string_list(stdout_map.get("contains"), "bug_signature.stdout.contains")) if stdout_map else None,
        stderr=StreamSignature(_as_string_list(stderr_map.get("contains"), "bug_signature.stderr.contains")) if stderr_map else None,
        files=FileSignature(
            exists=_as_string_list(files_map.get("exists"), "bug_signature.files.exists"),
            missing=_as_string_list(files_map.get("missing"), "bug_signature.files.missing"),
        ) if files_map else None,
    )

    setup = _as_mapping(raw.get("setup"), "setup")
    requirements = _as_mapping(raw.get("requirements"), "requirements")
    capture = _as_mapping(raw.get("capture"), "capture")
    redaction = _as_mapping(raw.get("redaction"), "redaction")
    _check_keys(setup, {"commands"}, "setup")
    _check_keys(requirements, {"commands"}, "requirements")
    _check_keys(capture, {"stdout", "stderr", "environment", "git"}, "capture")
    _check_keys(redaction, {"enabled"}, "redaction")
    if any(value is not True for value in [*capture.values(), *redaction.values()]):
        raise ReproLoadError("v1 capture/redaction flags, when specified, must be true")

    version = raw.get("version")
    if type(version) is not int:
        raise ReproLoadError("version must be an integer")
    name = raw.get("name", "")
    if not isinstance(name, str):
        raise ReproLoadError("name must be a string")
    workdir = raw.get("workdir", ".")
    if not isinstance(workdir, str):
        raise ReproLoadError("workdir must be a string")

    return ReproSpec(
        version=version,
        name=name,
        workdir=workdir,
        setup_commands=_as_string_list(setup.get("commands"), "setup.commands"),
        default_command=default_command,
        platform_commands=platform_commands,
        bug_signature=signature,
        required_commands=_as_string_list(requirements.get("commands"), "requirements.commands"),
        platforms=_as_string_list(raw.get("platforms"), "platforms"),
        capture=capture,
        redaction=redaction,
    )
