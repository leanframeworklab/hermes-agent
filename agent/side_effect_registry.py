"""Deterministic operation-level side-effect classification for governed tools."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CapabilitySpec:
    tool: str
    operation: str
    side_effect_level: int
    authority_required: str | None
    approval_required: bool
    hard_gate: bool
    secret_risk: str
    path_policy: str
    reversibility: str


class UnknownCapabilityError(ValueError):
    """Raised when a tool operation has no explicit capability declaration."""


def _spec(
    tool: str,
    operation: str,
    level: int,
    authority: str | None = None,
    approval: bool = False,
    hard_gate: bool = False,
    secret_risk: str = "NONE",
    path_policy: str = "NONE",
    reversibility: str = "NONE",
) -> CapabilitySpec:
    return CapabilitySpec(
        tool=tool,
        operation=operation,
        side_effect_level=level,
        authority_required=authority,
        approval_required=approval,
        hard_gate=hard_gate,
        secret_risk=secret_risk,
        path_policy=path_policy,
        reversibility=reversibility,
    )


_REGISTRY = {
    ("read_file", "read"): _spec("read_file", "read", 0, "path_policy", secret_risk="POSSIBLE", path_policy="CONTAINED"),
    ("skill_view", "view"): _spec("skill_view", "view", 0, "skill_authority", secret_risk="POSSIBLE", path_policy="MANAGED_SKILL"),
    ("skills_list", "list"): _spec("skills_list", "list", 0, "skill_authority", path_policy="MANAGED_SKILL"),
    ("search_files", "exact"): _spec("search_files", "exact", 0, "path_policy", secret_risk="POSSIBLE", path_policy="CONTAINED"),
    ("codegraph_query", "query"): _spec("codegraph_query", "query", 0, "project_authority", path_policy="CANONICAL_PROJECT"),
    ("codegraph_explore", "query"): _spec("codegraph_explore", "query", 0, "project_authority", path_policy="CANONICAL_PROJECT"),
    ("terminal", "git_status"): _spec("terminal", "git_status", 0, "git_authority", path_policy="CANONICAL_REPO"),
    ("terminal", "git_log"): _spec("terminal", "git_log", 0, "git_authority", path_policy="CANONICAL_REPO"),
    ("terminal", "git_rev_parse"): _spec("terminal", "git_rev_parse", 0, "git_authority", path_policy="CANONICAL_REPO"),
    ("terminal", "git_diff"): _spec("terminal", "git_diff", 0, "git_authority", path_policy="CANONICAL_REPO"),
    ("execute_code", "pure_calculation"): _spec("execute_code", "pure_calculation", 0, "sandbox"),
    ("pure_calculation", "calculate"): _spec("pure_calculation", "calculate", 0, "sandbox"),
    ("execute_code", "arbitrary"): _spec("execute_code", "arbitrary", 2, "execution_authority", hard_gate=True, secret_risk="POSSIBLE", reversibility="RECOVERABLE"),
    ("write_file", "write"): _spec("write_file", "write", 1, "workspace", hard_gate=True, secret_risk="POSSIBLE", path_policy="WORKSPACE", reversibility="REVERSIBLE"),
    ("apply_patch", "patch"): _spec("apply_patch", "patch", 1, "workspace", hard_gate=True, secret_risk="POSSIBLE", path_policy="WORKSPACE", reversibility="REVERSIBLE"),
    ("git", "stage"): _spec("git", "stage", 2, "git_authority", hard_gate=True, path_policy="CANONICAL_REPO", reversibility="RECOVERABLE"),
    ("git", "commit"): _spec("git", "commit", 2, "git_authority", hard_gate=True, path_policy="CANONICAL_REPO", reversibility="RECOVERABLE"),
    ("git", "push"): _spec("git", "push", 2, "git_authority", approval=True, hard_gate=True, path_policy="CANONICAL_REPO", reversibility="RECOVERABLE"),
    ("deploy", "deploy"): _spec("deploy", "deploy", 3, "deployment_authority", approval=True, hard_gate=True, secret_risk="POSSIBLE", reversibility="RECOVERABLE"),
    ("restart_service", "restart"): _spec("restart_service", "restart", 3, "service_authority", approval=True, hard_gate=True, reversibility="RECOVERABLE"),
    ("provider", "read"): _spec("provider", "read", 0, "provider_reader", secret_risk="HIGH"),
    ("provider", "mutate"): _spec("provider", "mutate", 4, "provider_authority", approval=True, hard_gate=True, secret_risk="HIGH", reversibility="IRREVERSIBLE"),
    ("campaign_play", "play"): _spec("campaign_play", "play", 4, "live_authorization", approval=True, hard_gate=True, secret_risk="HIGH", reversibility="IRREVERSIBLE"),
    ("spend", "spend"): _spec("spend", "spend", 4, "financial_authority", approval=True, hard_gate=True, secret_risk="HIGH", reversibility="IRREVERSIBLE"),
    ("delete", "delete"): _spec("delete", "delete", 4, "destructive_authority", approval=True, hard_gate=True, secret_risk="POSSIBLE", reversibility="IRREVERSIBLE"),
}


def _terminal_operation(command: Any) -> str | None:
    if not isinstance(command, str) or not command.strip():
        return None
    if any(token in command for token in (";", "|", "&", ">", "<", "$", "`", "(", ")")):
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    if len(parts) < 2 or parts[0] != "git":
        return None
    return {
        "status": "git_status",
        "log": "git_log",
        "rev-parse": "git_rev_parse",
        "diff": "git_diff",
    }.get(parts[1])


def classify_operation(tool: str, args: Mapping[str, Any] | None = None) -> CapabilitySpec:
    """Return explicit operation capability, failing closed for unknown input."""
    args = args or {}
    operation: str | None
    if tool == "terminal":
        operation = _terminal_operation(args.get("command"))
    elif tool == "execute_code":
        operation = "arbitrary"
    elif tool == "pure_calculation":
        operation = "calculate"
    elif tool in {"read_file"}:
        operation = "read"
    elif tool == "skill_view":
        operation = "view"
    elif tool == "skills_list":
        operation = "list"
    elif tool == "search_files":
        operation = "exact"
    elif tool in {"codegraph_query", "codegraph_explore"}:
        operation = "query"
    elif tool in {"write_file", "apply_patch"}:
        operation = "write" if tool == "write_file" else "patch"
    elif tool == "git":
        operation = str(args.get("operation") or "")
    elif tool == "provider":
        operation = str(args.get("operation") or "")
    elif tool == "campaign_play":
        operation = "play"
    elif tool == "spend":
        operation = "spend"
    elif tool == "delete":
        operation = "delete"
    elif tool in {"deploy", "restart_service"}:
        operation = "deploy" if tool == "deploy" else "restart"
    else:
        operation = None
    spec = _REGISTRY.get((tool, operation))
    if spec is None:
        raise UnknownCapabilityError(f"unknown tool operation: {tool}:{operation or '<none>'}")
    return spec


def registry_snapshot() -> tuple[CapabilitySpec, ...]:
    return tuple(_REGISTRY.values())
