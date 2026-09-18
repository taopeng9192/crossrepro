from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class PatternRule:
    kind: str
    pattern: re.Pattern[str]
    high_risk: bool
    replacement_group: int = 0


PATTERNS = [
    PatternRule(
        "cookie",
        re.compile(r"(?im)\b((?:set-cookie|cookie):[ \t]*)(?![ \t]*\[COOKIE_\d+\](?:\r?$))([^\r\n]+)"),
        True,
        2,
    ),
    PatternRule(
        "authorization",
        re.compile(r"(?im)\b(authorization:[ \t]*)(?![ \t]*(?:Bearer\b|\[AUTHORIZATION_\d+\](?:\r?$)))([^\r\n]+)"),
        True,
        2,
    ),
    PatternRule(
        "private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            re.DOTALL,
        ),
        True,
    ),
    PatternRule(
        "bearer_token",
        re.compile(r"(?i)(Authorization:\s*Bearer\s+|Bearer\s+)([A-Za-z0-9._~+/=-]{12,})"),
        True,
        2,
    ),
    PatternRule(
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
        True,
    ),
    PatternRule(
        "aws_access_key",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        True,
    ),
    PatternRule(
        "openai_style_key",
        re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
        True,
    ),
    PatternRule(
        "github_token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
        True,
    ),
    PatternRule(
        "stripe_secret",
        re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"),
        True,
    ),
    PatternRule(
        "api_key_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)\b[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_\-./+=]{8,})[\"']?"
        ),
        True,
        2,
    ),
    PatternRule(
        "credential_url",
        re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/:]+:[^\s/@]+@[^\s]+"),
        True,
    ),
    PatternRule(
        "windows_username",
        re.compile(r"(?i)([A-Z]:\\{1,2}Users\\{1,2})([^\\/\s\"']+)"),
        False,
        2,
    ),
    PatternRule(
        "posix_username",
        re.compile(r"(/(?:home|Users)/)([^/\s]+)"),
        False,
        2,
    ),
    PatternRule(
        "email",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        False,
    ),
]
