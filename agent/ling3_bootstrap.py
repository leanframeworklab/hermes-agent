"""Deterministic Ling 3 bootstrap packet compiler."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

SCHEMA_VERSION = "lah-ling3-bootstrap-v1"
_MODES = {"READ_ONLY_AUDIT", "DESIGN_ONLY", "DIAGNOSTIC", "REPAIR", "EXECUTE", "BUILD_AND_CERTIFY"}
_FAMILIES = {"MATH_CERTIFICATION", "READ_ONLY_AUDIT", "GIT", "CODE", "RUNTIME", "DEPLOYMENT", "PROVIDER", "UNKNOWN"}


def _family(text: str) -> str:
    value = text.lower()
    if re.search(r"\b(math|mathematical|calculation|arithmetic|formula)\b", value):
        return "MATH_CERTIFICATION"
    if re.search(r"\b(skill\.md|read.only|dump|print|inspect|audit)\b", value) and not re.search(r"\b(repair|fix|modify)\b", value):
        return "READ_ONLY_AUDIT"
    if re.search(r"\b(git|commit|branch|worktree|merge|pull request|pr)\b", value):
        return "GIT"
    if re.search(r"\b(deploy|deployment|restart|service)\b", value):
        return "DEPLOYMENT"
    if re.search(r"\b(provider|campaign|play|spend|approval|exoclick|lahb)\b", value):
        return "PROVIDER"
    if re.search(r"\b(repair|fix|code|implementation|structural|module|symbol)\b", value):
        return "CODE"
    if re.search(r"\b(runtime|hermes|dispatch|governance)\b", value):
        return "RUNTIME"
    return "UNKNOWN"


def _mode(text: str, explicit: str | None) -> str:
    if explicit and explicit in _MODES:
        return explicit
    value = text.lower()
    if re.search(r"\b(design.only|audit|read.only|inspect|dump)\b", value):
        return "DESIGN_ONLY" if "design" in value else "READ_ONLY_AUDIT"
    if re.search(r"\b(build.and.certify|build)\b", value):
        return "BUILD_AND_CERTIFY"
    if re.search(r"\b(repair|fix)\b", value):
        return "REPAIR"
    if re.search(r"\b(certif|prove|verify)\b", value):
        return "DIAGNOSTIC"
    return "DIAGNOSTIC"


def _requirements(family: str, mode: str, level: int, repos: int, workstreams: int, gates: int, actions: int) -> dict[str, str | bool]:
    codegraph = "UNNECESSARY"
    if family in {"CODE", "RUNTIME"} and ("structural" in family.lower() or mode in {"REPAIR", "RUNTIME"}):
        codegraph = "REQUIRED"
    elif family not in {"MATH_CERTIFICATION", "READ_ONLY_AUDIT"}:
        codegraph = "OPTIONAL"
    if family == "CODE" and mode == "REPAIR":
        codegraph = "REQUIRED"
    decomposition = "BYPASS"
    if (
        repos >= 2 or workstreams >= 2 or gates >= 4 or actions > 6 or mode == "BUILD_AND_CERTIFY"
        or (level >= 2 and gates >= 2)
    ):
        decomposition = "REQUIRED"
    elif level > 0:
        decomposition = "OPTIONAL"
    return {"codegraph": codegraph, "decomposition": decomposition, "research": "BYPASS" if family in {"MATH_CERTIFICATION", "READ_ONLY_AUDIT"} else "OPTIONAL"}


def _level(text: str, action: Mapping[str, Any] | None) -> int:
    value = text.lower()
    if re.search(r"\b(play|spend|provider mutation|campaign create|financial)\b", value):
        return 4
    if re.search(r"\b(deploy|restart service|runtime mutation)\b", value):
        return 3
    if re.search(r"\b(commit|push|merge|persistent repository|authority mutation)\b", value):
        return 2
    if action and action.get("tool") == "execute_code":
        return 2
    if re.search(r"\b(write|patch|edit|modify|repair)\b", value):
        return 1
    return 0


def _hash(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def validate_bootstrap_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    if packet.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("schema_version")
    if not isinstance(packet.get("side_effect_level"), int) or not 0 <= packet["side_effect_level"] <= 4:
        raise ValueError("side_effect_level")
    if packet.get("state") not in {"BOOT", "RESOLVE", "PLAN", "EXECUTE", "VERIFY", "PERSIST", "REPORT"}:
        raise ValueError("state")
    if packet.get("mission_mode") not in _MODES:
        raise ValueError("mission_mode")
    if packet.get("problem_family") not in _FAMILIES:
        raise ValueError("problem_family")
    action = packet.get("next_action") or {}
    tool = action.get("tool")
    if tool is not None and tool not in packet.get("allowed_tools", []):
        raise ValueError("next_action.tool")
    if packet["side_effect_level"] >= 2 and action.get("tool") is not None and packet["route"].get("decision") != "RESOLVED":
        raise ValueError("route required before persistent action")
    return dict(packet)


def compile_bootstrap_packet(
    *,
    mission_id: str,
    mission_text: str,
    mission_mode: str | None = None,
    route: Mapping[str, Any] | None = None,
    certified_context: Mapping[str, Any] | None = None,
    resume: Mapping[str, Any] | None = None,
    fingerprint_valid: bool = True,
    initial_action: Mapping[str, Any] | None = None,
    acceptance_gates: int = 0,
    planned_actions: int = 0,
    independent_workstreams: int = 0,
) -> dict[str, Any]:
    if not isinstance(mission_id, str) or not mission_id:
        raise ValueError("mission_id")
    text = mission_text if isinstance(mission_text, str) else ""
    mode = _mode(text, mission_mode)
    family = _family(text)
    level = _level(text, initial_action)
    route_value = dict(route or {"decision": "RESOLVED" if level == 0 else "AMBIGUOUS"})
    route_value.setdefault("decision", "AMBIGUOUS")
    requirements = _requirements(
        family,
        mode,
        level,
        len(route_value.get("context_repos", [])) + (1 if route_value.get("repository_authority") else 0),
        independent_workstreams,
        acceptance_gates,
        planned_actions,
    )
    allowed = ["read_file", "skill_view", "search_files", "git", "terminal", "codegraph_query", "codegraph_explore"]
    if family == "MATH_CERTIFICATION":
        allowed = ["pure_calculation"]
    if initial_action:
        action_tool = initial_action.get("tool")
        if action_tool not in allowed:
            raise ValueError("next_action.tool")
        next_action = {"tool": action_tool, "arguments": dict(initial_action.get("arguments") or {})}
    else:
        next_action = {"tool": None, "arguments": {}}
    packet = {
        "schema_version": SCHEMA_VERSION,
        "mission_id": mission_id,
        "state": "EXECUTE" if initial_action else "PLAN",
        "mission_mode": mode,
        "problem_family": family,
        "side_effect_level": level,
        "route": route_value,
        "authority": {"manifest_valid": True, "source_runtime_parity": "UNKNOWN", "fingerprint_valid": fingerprint_valid},
        "certified_context": {"present": certified_context is not None, "fingerprint": _hash(certified_context) if certified_context else None, "facts": dict(certified_context or {})},
        "resume": {"present": resume is not None, "checkpoint": (resume or {}).get("current_checkpoint"), "next_action": (resume or {}).get("next_action"), "blocking_unknowns": list((resume or {}).get("blocking_unknowns", []))},
        "requirements": requirements,
        "facts": {},
        "allowed_tools": allowed,
        "forbidden_tools": ["campaign_play", "spend", "provider", "deploy", "restart_service", "delete"],
        "hard_blockers": ([] if fingerprint_valid else ["RESUME_FINGERPRINT_MISMATCH"]) + (["OPERATOR_APPROVAL_REQUIRED"] if level >= 4 else []),
        "jit_refs": [family] if family not in {"MATH_CERTIFICATION", "READ_ONLY_AUDIT"} else [],
        "next_action": next_action,
    }
    return validate_bootstrap_packet(packet)
