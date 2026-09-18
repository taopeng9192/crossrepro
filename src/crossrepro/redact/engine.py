from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .patterns import PATTERNS, PatternRule


@dataclass(slots=True)
class RedactionMatch:
    kind: str
    line: int
    placeholder: str
    high_risk: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class RedactionResult:
    text: str
    matches: list[RedactionMatch]

    def to_report(self) -> dict:
        return {
            "total_matches": len(self.matches),
            "high_risk_matches": sum(1 for match in self.matches if match.high_risk),
            "matches": [match.to_dict() for match in self.matches],
        }


def _span(rule: PatternRule, match) -> tuple[int, int]:
    return match.span(rule.replacement_group)


def _find_matches(text: str):
    candidates = []
    counters: dict[str, int] = {}
    for rule in PATTERNS:
        for match in rule.pattern.finditer(text):
            start, end = _span(rule, match)
            counters[rule.kind] = counters.get(rule.kind, 0) + 1
            placeholder = f"[{rule.kind.upper()}_{counters[rule.kind]}]"
            candidates.append((start, end, rule.kind, placeholder, rule.high_risk))
    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    filtered = []
    last_end = -1
    for item in candidates:
        start, end = item[0], item[1]
        if start >= last_end:
            filtered.append(item)
            last_end = end
    return filtered


def redact_text(text: str) -> RedactionResult:
    filtered = _find_matches(text)
    output = text
    matches_out: list[RedactionMatch] = []
    for start, end, kind, placeholder, high_risk in sorted(filtered, key=lambda item: item[0], reverse=True):
        line = text.count("\n", 0, start) + 1
        output = output[:start] + placeholder + output[end:]
        matches_out.append(RedactionMatch(kind=kind, line=line, placeholder=placeholder, high_risk=high_risk))
    matches_out.reverse()
    return RedactionResult(text=output, matches=matches_out)


def contains_high_risk_secret(text: str) -> bool:
    return any(rule.high_risk and rule.pattern.search(text) for rule in PATTERNS)


def redact_data(value, *, matches: list[RedactionMatch] | None = None):
    """Redact before serialization so quotes and backslashes stay valid JSON."""
    if isinstance(value, str):
        result = redact_text(value)
        if matches is not None:
            matches.extend(result.matches)
        return result.text
    if isinstance(value, dict):
        return {redact_data(key, matches=matches): redact_data(item, matches=matches) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_data(item, matches=matches) for item in value]
    return value


def redact_json(value) -> RedactionResult:
    matches: list[RedactionMatch] = []
    safe = redact_data(value, matches=matches)
    return RedactionResult(json.dumps(safe, indent=2), matches)
