from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CommandSpec:
    run: str
    shell: str | None = None


@dataclass(slots=True)
class ExitCodeSignature:
    equals: int | None = None
    mode: str | None = None


@dataclass(slots=True)
class StreamSignature:
    contains: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FileSignature:
    exists: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BugSignature:
    exit_code: ExitCodeSignature | None = None
    stdout: StreamSignature | None = None
    stderr: StreamSignature | None = None
    files: FileSignature | None = None


@dataclass(slots=True)
class ReproSpec:
    version: int
    name: str
    workdir: str
    setup_commands: list[str]
    default_command: CommandSpec
    platform_commands: dict[str, CommandSpec]
    bug_signature: BugSignature
    required_commands: list[str]
    platforms: list[str]
    capture: dict = field(default_factory=dict)
    redaction: dict = field(default_factory=dict)

    def command_for(self, platform_key: str) -> CommandSpec:
        return self.platform_commands.get(platform_key, self.default_command)
