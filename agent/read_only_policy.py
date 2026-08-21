"""Deterministic level-zero tool policy.

This module does not decide mission workflow. It proves whether a requested
operation is safe enough to pass workflow bootstrap.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from agent.side_effect_registry import UnknownCapabilityError, classify_operation


class ReadOnlyDecision(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_REDACTION = "ALLOW_WITH_REDACTION"
    BLOCK_SECRET = "BLOCK_SECRET"
    BLOCK_PATH_ESCAPE = "BLOCK_PATH_ESCAPE"
    BLOCK_UNKNOWN_TOOL = "BLOCK_UNKNOWN_TOOL"
    BLOCK_HIDDEN_MUTATION = "BLOCK_HIDDEN_MUTATION"


@dataclass(frozen=True)
class ReadOnlyResult:
    decision: ReadOnlyDecision
    reason: str = ""
    redaction_required: bool = False


_SECRET_NAMES = re.compile(
    r"(?:^|[._-])(env|secret|secrets|credential|credentials|token|password|passwd|private[_-]?key)(?:$|[._-])",
    re.IGNORECASE,
)
_FORBIDDEN_CODE = re.compile(
    r"\b(?:import|__import__|open|exec|eval|compile|input|socket|subprocess|os|pathlib|shutil|ctypes|dlopen|requests|urllib)\b|[;&|<>`]",
    re.IGNORECASE,
)


def _path_from_args(tool: str, args: Mapping[str, Any]) -> str | None:
    if tool in {"read_file", "search_files"}:
        value = args.get("path")
        return value if isinstance(value, str) else None
    return None


def _contained(path: str, roots: list[str]) -> bool:
    if not roots:
        return False
    if any(part == ".." for part in Path(path).parts):
        return False
    candidate = os.path.realpath(path if os.path.isabs(path) else os.path.join(os.getcwd(), path))
    return any(os.path.commonpath([candidate, os.path.realpath(root)]) == os.path.realpath(root) for root in roots)


def _safe_terminal(command: Any) -> bool:
    if not isinstance(command, str) or not command.strip():
        return False
    if any(token in command for token in (";", "|", "&", ">", "<", "$", "`", "(", ")")):
        return False
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    return len(parts) >= 2 and parts[0] == "git" and parts[1] in {"status", "log", "rev-parse", "diff"}


def evaluate_read_only(tool: str, args: Mapping[str, Any] | None = None) -> ReadOnlyResult:
    args = args or {}
    try:
        spec = classify_operation(tool, args)
    except UnknownCapabilityError as exc:
        return ReadOnlyResult(ReadOnlyDecision.BLOCK_UNKNOWN_TOOL, str(exc))

    if spec.side_effect_level != 0:
        return ReadOnlyResult(ReadOnlyDecision.BLOCK_HIDDEN_MUTATION, "operation is not level zero")

    if tool == "execute_code":
        return ReadOnlyResult(ReadOnlyDecision.BLOCK_HIDDEN_MUTATION, "execute_code is arbitrary execution")

    if tool == "pure_calculation":
        code = args.get("code")
        limits = args.get("limits") or {}
        if not isinstance(code, str) or args.get("sandbox_profile") != "pure_calculation_v1":
            return ReadOnlyResult(ReadOnlyDecision.BLOCK_HIDDEN_MUTATION, "pure calculation mode required")
        if not (
            isinstance(limits, Mapping)
            and limits.get("cpu_operations") == 100
            and limits.get("memory_bytes") == 131072
            and limits.get("output_chars") == 4096
            and limits.get("wall_time_ms") == 2000
        ):
            return ReadOnlyResult(ReadOnlyDecision.BLOCK_HIDDEN_MUTATION, "pure calculation limits are not certified")
        if _FORBIDDEN_CODE.search(code):
            return ReadOnlyResult(ReadOnlyDecision.BLOCK_HIDDEN_MUTATION, "calculation contains forbidden capability")
        if len(code) > 16_384:
            return ReadOnlyResult(ReadOnlyDecision.BLOCK_HIDDEN_MUTATION, "calculation output/input exceeds bound")
        return ReadOnlyResult(ReadOnlyDecision.ALLOW)

    if tool == "terminal":
        if not _safe_terminal(args.get("command")):
            return ReadOnlyResult(ReadOnlyDecision.BLOCK_HIDDEN_MUTATION, "terminal command is not allowlisted")
        return ReadOnlyResult(ReadOnlyDecision.ALLOW)

    if tool == "search_files" and not args.get("exact"):
        return ReadOnlyResult(ReadOnlyDecision.BLOCK_HIDDEN_MUTATION, "only exact-path search is level zero")

    if tool in {"codegraph_query", "codegraph_explore"}:
        project = args.get("project_path") or args.get("canonical_repo")
        roots = args.get("allowed_roots") or ([project] if isinstance(project, str) else [])
        if not isinstance(project, str) or not _contained(project, list(roots)):
            return ReadOnlyResult(ReadOnlyDecision.BLOCK_PATH_ESCAPE, "unauthorized CodeGraph project boundary")
        return ReadOnlyResult(ReadOnlyDecision.ALLOW)

    path = _path_from_args(tool, args)
    if path is not None:
        roots = args.get("allowed_roots")
        if not isinstance(roots, list) or not _contained(path, roots):
            return ReadOnlyResult(ReadOnlyDecision.BLOCK_PATH_ESCAPE, "path escapes declared roots")
        name = Path(path).name
        if _SECRET_NAMES.search(name):
            if args.get("redact") is True:
                return ReadOnlyResult(ReadOnlyDecision.ALLOW_WITH_REDACTION, "secret-like path requires redaction", True)
            return ReadOnlyResult(ReadOnlyDecision.BLOCK_SECRET, "secret-like path requires redaction")
        return ReadOnlyResult(ReadOnlyDecision.ALLOW)

    if tool == "skill_view":
        name = args.get("name")
        canonical_names = {
            "lah-workflow", "lah-workflow-small-model", "lah-workflow-ling3",
            "lah-repo-router", "mission-decomposer",
        }
        if not isinstance(name, str) or name not in canonical_names:
            return ReadOnlyResult(ReadOnlyDecision.BLOCK_PATH_ESCAPE, "invalid managed skill name")
        return ReadOnlyResult(ReadOnlyDecision.ALLOW)

    if tool == "skills_list":
        return ReadOnlyResult(ReadOnlyDecision.ALLOW)

    return ReadOnlyResult(ReadOnlyDecision.ALLOW)
