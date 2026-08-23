"""Fail-closed secret boundary for command, tool, log, and receipt output.

This module is deliberately independent from user-configurable display
redaction.  Callers at security boundaries must use this module so an opt-out
for debugging cannot return raw output.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Mapping


OUTPUT_WITHHELD = "OUTPUT_WITHHELD"
_WITHHELD_TEXT = "[OUTPUT_WITHHELD]"


@dataclass(frozen=True)
class SanitizedOutput:
    text: str
    secret_detected: bool = False
    redaction_count: int = 0
    redaction_classes: tuple[str, ...] = ()
    source_stream: str = "unknown"
    status: str = "OK"


@dataclass(frozen=True)
class SanitizedValue:
    value: Any
    secret_detected: bool = False
    redaction_count: int = 0
    redaction_classes: tuple[str, ...] = ()
    status: str = "OK"


class SecretBoundaryFormatter(logging.Formatter):
    """Logging formatter that never emits raw text if sanitization fails."""

    def format(self, record: logging.LogRecord) -> str:
        try:
            return sanitize_secret_output(super().format(record), source_stream="log").text
        except Exception:
            return _WITHHELD_TEXT


_PLACEHOLDER = {
    "credential": "[REDACTED:credential]",
    "github_token": "[REDACTED:github_token]",
    "bearer_token": "[REDACTED:bearer_token]",
    "password": "[REDACTED:password]",
    "private_key": "[REDACTED:private_key]",
    "jwt": "[REDACTED:jwt]",
    "high_entropy_secret": "[REDACTED:high_entropy_secret]",
}

_SECRET_KEY = r"(?:token|access[_-]?token|refresh[_-]?token|api[_-]?key|apikey|secret|password|passwd|private[_-]?key|client[_-]?secret|authorization|bearer|cookie|session|credential)"
_KEY_VALUE_RE = re.compile(
    r"(?P<key>\b[A-Za-z_][A-Za-z0-9_.-]*\b)"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<quote>['\"]?)"
    r"(?P<value>[^\s,}\]:'\"]+)"
    r"(?P=quote)",
    re.IGNORECASE,
)
_JSON_FIELD_RE = re.compile(
    rf'(?P<key>"{_SECRET_KEY}")(?P<sep>\s*:\s*)(?P<quote>")(?P<value>(?:\\.|[^"\\])*)(?P=quote)',
    re.IGNORECASE,
)
_CLI_OPTION_RE = re.compile(
    rf"(?P<key>--?(?:{_SECRET_KEY}))(?P<sep>\s*=\s*|\s+)(?P<quote>['\"]?)(?P<value>[^\s,'\"]+)(?P=quote)",
    re.IGNORECASE,
)
_AUTH_RE = re.compile(
    r"(?P<prefix>\bAuthorization\s*:\s*)(?P<scheme>Bearer|Basic)\s+(?P<value>\S+)",
    re.IGNORECASE,
)
_GITHUB_RE = re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{10,}\b|\bgithub_pat_[A-Za-z0-9_]{10,}\b")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b")
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----[\s\S]*?-----END(?: [A-Z0-9]+)* PRIVATE KEY-----"
)
_URL_USERINFO_RE = re.compile(
    r"(?P<prefix>\b(?:https?|wss?|ftp)://[^/\s:@]+:)(?P<value>[^/\s@]+)(?P<suffix>@)",
    re.IGNORECASE,
)
_URL_QUERY_RE = re.compile(
    rf"(?P<prefix>[?&](?:{_SECRET_KEY})=)(?P<value>[^&#\s]+)",
    re.IGNORECASE,
)
_HIGH_ENTROPY_CONTEXT_RE = re.compile(
    r"\b(?:secret|credential|opaque)\s+(?:value\s+)?(?P<value>[A-Za-z0-9+/=_-]{32,})\b",
    re.IGNORECASE,
)
_SECRET_LIKE_RE = re.compile(r"(?<![A-Za-z0-9_-])(?P<value>[A-Za-z0-9][A-Za-z0-9_-]{23,})(?![A-Za-z0-9_-])")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
_SECRET_KEY_NAME_RE = re.compile(
    rf"(?:^|[_-])(?:{_SECRET_KEY})(?:$|[_-](?:value|input|material|body|header|credential|key|token|secret|password))",
    re.IGNORECASE,
)


def _mask(kind: str) -> str:
    return _PLACEHOLDER[kind]


def _looks_high_entropy(value: str) -> bool:
    """Require mixed character classes and entropy before generic matching."""
    if len(value) < 24 or _UUID_RE.fullmatch(value):
        return False
    if len(value) in {40, 64} and all(char in "0123456789abcdefABCDEF" for char in value):
        return False
    classes = sum((any(char.islower() for char in value),
                   any(char.isupper() for char in value),
                   any(char.isdigit() for char in value),
                   any(not char.isalnum() for char in value)))
    if classes < 3:
        return False
    import math
    entropy = -sum((value.count(char) / len(value)) * math.log2(value.count(char) / len(value)) for char in set(value))
    return entropy >= 3.2


def _sanitize_text(text: str) -> tuple[str, int, set[str]]:
    """Sanitize text. Raises on programming defects; public API withholds."""
    count = 0
    classes: set[str] = set()

    def replace(pattern, kind, match_text=None):
        nonlocal text, count

        def callback(match: re.Match) -> str:
            nonlocal count
            count += 1
            classes.add(kind)
            if match_text is not None:
                return match_text(match)
            return _mask(kind)

        text = pattern.sub(callback, text)

    replace(_PRIVATE_KEY_RE, "private_key")
    replace(_AUTH_RE, "bearer_token", lambda m: f"{m.group('prefix')}{m.group('scheme')} {_mask('bearer_token')}" if m.group('scheme').lower() == "bearer" else f"{m.group('prefix')}{m.group('scheme')} {_mask('credential')}")
    replace(_GITHUB_RE, "github_token")
    replace(_JWT_RE, "jwt")
    replace(_URL_USERINFO_RE, "password", lambda m: f"{m.group('prefix')}{_mask('password')}{m.group('suffix')}")
    replace(_URL_QUERY_RE, "credential", lambda m: f"{m.group('prefix')}{_mask('credential')}")

    def key_value(match: re.Match) -> str:
        nonlocal count
        key_name = match.group("key").strip('"')
        if not _SECRET_KEY_NAME_RE.search(key_name):
            return match.group(0)
        value = match.group("value")
        if value.startswith("[REDACTED:"):
            return match.group(0)
        count += 1
        classes.add("credential")
        return f"{match.group('key')}{match.group('sep')}{match.group('quote')}{_mask('credential')}{match.group('quote')}"

    text = _JSON_FIELD_RE.sub(key_value, text)
    text = _KEY_VALUE_RE.sub(key_value, text)
    text = _CLI_OPTION_RE.sub(key_value, text)

    def high_entropy(match: re.Match) -> str:
        nonlocal count
        count += 1
        classes.add("high_entropy_secret")
        return match.group(0).replace(match.group("value"), _mask("high_entropy_secret"))

    text = _HIGH_ENTROPY_CONTEXT_RE.sub(high_entropy, text)

    def generic_secret(match: re.Match) -> str:
        nonlocal count
        value = match.group("value")
        if not _looks_high_entropy(value):
            return value
        count += 1
        classes.add("high_entropy_secret")
        return _mask("high_entropy_secret")

    text = _SECRET_LIKE_RE.sub(generic_secret, text)

    return text, count, classes


def sanitize_secret_output(value: Any, *, source_stream: str = "unknown") -> SanitizedOutput:
    """Return sanitized output, never raw output when processing fails."""
    try:
        text = value if isinstance(value, str) else str(value)
        sanitized, count, classes = _sanitize_text(text)
        return SanitizedOutput(
            text=sanitized,
            secret_detected=count > 0,
            redaction_count=count,
            redaction_classes=tuple(sorted(classes)),
            source_stream=source_stream,
        )
    except Exception:
        return SanitizedOutput(
            text=_WITHHELD_TEXT,
            secret_detected=True,
            source_stream=source_stream,
            status=OUTPUT_WITHHELD,
        )


def sanitize_command_display(command: Any) -> SanitizedOutput:
    return sanitize_secret_output(command, source_stream="command")


def sanitize_exception(exc: BaseException) -> SanitizedOutput:
    return sanitize_secret_output(str(exc), source_stream="exception")


_SENSITIVE_MAPPING_KEYS = re.compile(rf"^{_SECRET_KEY}$", re.IGNORECASE)


def sanitize_mapping(value: Any) -> SanitizedValue:
    """Sanitize structured receipt/log data without retaining secret values."""
    try:
        classes: set[str] = set()
        count = 0

        def walk(item: Any) -> Any:
            nonlocal count
            if isinstance(item, Mapping):
                result = {}
                for key, child in item.items():
                    key_text = str(key)
                    if _SENSITIVE_MAPPING_KEYS.match(key_text):
                        result[key] = _mask("credential")
                        count += 1
                        classes.add("credential")
                    else:
                        result[key] = walk(child)
                return result
            if isinstance(item, list):
                return [walk(child) for child in item]
            if isinstance(item, tuple):
                return tuple(walk(child) for child in item)
            if isinstance(item, str):
                result = sanitize_secret_output(item)
                count += result.redaction_count
                classes.update(result.redaction_classes)
                return result.text
            return item

        sanitized = walk(value)
        return SanitizedValue(
            value=sanitized,
            secret_detected=count > 0,
            redaction_count=count,
            redaction_classes=tuple(sorted(classes)),
        )
    except Exception:
        return SanitizedValue(value={"status": OUTPUT_WITHHELD}, secret_detected=True, status=OUTPUT_WITHHELD)


def sanitize_environment_metadata(environment: Mapping[str, Any]) -> dict[str, dict[str, bool]]:
    """Expose only presence metadata; never values or value-derived data."""
    return {str(key): {"present": value is not None and value != ""} for key, value in environment.items()}


_BLOCKED_COMMAND_PATTERNS = (
    re.compile(r"\bgh\s+auth\s+token\b", re.IGNORECASE),
    re.compile(r"\bgh\s+auth\s+status\b[^\n]*--show-token\b", re.IGNORECASE),
    re.compile(r"\bgit\s+credential\s+(?:fill|get)\b", re.IGNORECASE),
    re.compile(r"\bcredential[-_]helper\s+(?:get|fill)\b", re.IGNORECASE),
    re.compile(r"\b(?:cat|head|tail|sed|less|more)\b[^\n]*(?:hosts\.yml|credentials|secret|\.env)\b", re.IGNORECASE),
    re.compile(r"\bprintenv\b[^\n]*(?:TOKEN|API[_-]?KEY|SECRET|PASSWORD|PRIVATE[_-]?KEY)\b", re.IGNORECASE),
    re.compile(r"\becho\b[^\n]*\$(?:GH_TOKEN|GITHUB_TOKEN|[A-Z0-9_]*(?:TOKEN|API[_-]?KEY|SECRET|PASSWORD))\b", re.IGNORECASE),
    re.compile(r"^\s*(?:env|set|export)\s*$", re.IGNORECASE),
)


def classify_secret_command(command: Any) -> dict[str, Any]:
    """Block direct credential-dump commands while allowing metadata checks."""
    display = sanitize_command_display(command)
    text = command if isinstance(command, str) else str(command)
    for pattern in _BLOCKED_COMMAND_PATTERNS:
        if pattern.search(text):
            return {"allowed": False, "status": "blocked", "reason": "secret_output_command", "command": display.text}
    return {"allowed": True, "status": "allowed", "command": display.text}
