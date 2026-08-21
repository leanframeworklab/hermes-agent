"""Narrow governed-workflow bootstrap and capability policy."""

from __future__ import annotations

import json
import os
import re
import shlex
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from agent.read_only_policy import ReadOnlyDecision, evaluate_read_only
from agent.side_effect_registry import UnknownCapabilityError, classify_operation


class GovernancePhase(str, Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    ORCHESTRATOR_REQUIRED = "ORCHESTRATOR_REQUIRED"
    ROUTER_REQUIRED = "ROUTER_REQUIRED"
    ROUTER_PASSED = "ROUTER_PASSED"
    DECOMPOSER_REQUIRED = "DECOMPOSER_REQUIRED"
    GOVERNANCE_PREREQUISITES_PASSED = "GOVERNANCE_PREREQUISITES_PASSED"
    ROUTER_FAILED = "ROUTER_FAILED"
    DECOMPOSER_FAILED = "DECOMPOSER_FAILED"
    MANDATORY_SKILL_MISSING = "MANDATORY_SKILL_MISSING"
    MANDATORY_SKILL_RESOLUTION_FAILED = "MANDATORY_SKILL_RESOLUTION_FAILED"
    MANDATORY_SKILL_LOAD_FAILED = "MANDATORY_SKILL_LOAD_FAILED"
    MANDATORY_GATE_ORDER_INVALID = "MANDATORY_GATE_ORDER_INVALID"


class GovernanceMode(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED_READ_ONLY = "DEGRADED_READ_ONLY"
    BLOCKED_DANGEROUS_ACTION = "BLOCKED_DANGEROUS_ACTION"


class ToolCapability(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOCAL_ENGINEERING_WRITE = "LOCAL_ENGINEERING_WRITE"
    EXTERNAL_MUTATION = "EXTERNAL_MUTATION"
    FINANCIAL = "FINANCIAL"
    PLAY = "PLAY"
    DEPLOYMENT = "DEPLOYMENT"
    DESTRUCTIVE = "DESTRUCTIVE"
    UNKNOWN = "UNKNOWN"


ORCHESTRATOR = "lah-workflow-small-model"
MANDATORY_SKILLS = {
    GovernancePhase.ORCHESTRATOR_REQUIRED: ("entry", ORCHESTRATOR),
    GovernancePhase.ROUTER_REQUIRED: ("0", "lah-repo-router"),
    GovernancePhase.DECOMPOSER_REQUIRED: ("0.5", "mission-decomposer"),
}
READ_ONLY_TOOLS = frozenset({
    "skill_view", "skills_list", "read_file", "search_files", "session_search",
    "codegraph_query", "codegraph_explore", "governance_status", "runtime_diagnostics",
})
# Compatibility name retained for callers that only need metadata discovery.
GOVERNANCE_METADATA_TOOLS = READ_ONLY_TOOLS
LOCAL_ENGINEERING_WRITE_TOOLS = frozenset({"write_file", "apply_patch", "local_edit"})
EXTERNAL_MUTATION_TOOLS = frozenset({
    "campaign_create", "campaign_update", "campaign_provider_mutate", "provider_update",
    "provider_mutation", "external_mutation", "account_mutate",
})
FINANCIAL_TOOLS = frozenset({"financial_action", "spend", "payment", "purchase"})
PLAY_TOOLS = frozenset({"campaign_play", "play", "CAMPAIGN_PLAY"})
DEPLOYMENT_TOOLS = frozenset({"deploy", "deployment", "goes_request", "restart_service"})
DESTRUCTIVE_TOOLS = frozenset({"delete", "destroy", "destructive_operation"})


def classify_governed_mission(text: str | None) -> bool:
    value = (text or "").lower()
    return bool(
        re.search(r"\blah-workflow(?:-small-model|-ling3)?\b", value)
        or re.search(r"\bgoverned\s+lah\s+mission\b", value)
        or re.search(r"\bmission\s*:\s*lah_[a-z0-9_]+", value)
        or (re.search(r"\bmission\b", value) and re.search(r"\blah_[a-z0-9_]+\b", value)
            and re.search(r"\blah-repo-router\b|\bmission-decomposer\b", value))
    )


def _safe_read_only_terminal(command: Any) -> bool:
    if not isinstance(command, str) or not command.strip():
        return False
    if any(token in command for token in (";", "|", "&", ">", "<", "$", "`", "(", ")")):
        return False
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if not parts:
        return False
    if parts[0] == "git":
        return len(parts) > 1 and parts[1] in {"status", "log", "diff", "show", "branch", "rev-parse"}
    return parts[0] in {"cat", "head", "tail", "ls", "pwd", "rg", "sed", "find", "stat", "file"}


def classify_tool_capability(tool_name: str, args: Mapping[str, Any] | None = None) -> ToolCapability:
    """Classify canonical tool identity; caller-provided labels are ignored."""
    if tool_name in READ_ONLY_TOOLS or (tool_name == "terminal" and _safe_read_only_terminal((args or {}).get("command"))):
        return ToolCapability.READ_ONLY
    if tool_name in LOCAL_ENGINEERING_WRITE_TOOLS:
        return ToolCapability.LOCAL_ENGINEERING_WRITE
    if tool_name in EXTERNAL_MUTATION_TOOLS:
        return ToolCapability.EXTERNAL_MUTATION
    if tool_name in FINANCIAL_TOOLS:
        return ToolCapability.FINANCIAL
    if tool_name in PLAY_TOOLS:
        return ToolCapability.PLAY
    if tool_name in DEPLOYMENT_TOOLS:
        return ToolCapability.DEPLOYMENT
    if tool_name in DESTRUCTIVE_TOOLS:
        return ToolCapability.DESTRUCTIVE
    return ToolCapability.UNKNOWN


@dataclass(frozen=True)
class GovernanceDecision:
    allowed: bool
    result: str = ""


@dataclass
class GovernedSkillState:
    governed: bool = False
    authority_valid: bool = True
    authority_errors: tuple[str, ...] = ()
    phase: GovernancePhase = GovernancePhase.UNCLASSIFIED
    failure_reason: str = ""
    certified_routing_established: bool = False
    canonical_repo: str | None = None
    observed: list[dict[str, Any]] = field(default_factory=list)
    bootstrap_packet: Mapping[str, Any] | None = None
    native_workflow: bool = False
    _denial_fingerprints: dict[str, int] = field(default_factory=dict, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def __post_init__(self) -> None:
        if not self.governed or self.phase is not GovernancePhase.UNCLASSIFIED:
            return
        if not self.authority_valid:
            self.phase = GovernancePhase.MANDATORY_SKILL_RESOLUTION_FAILED
            self.failure_reason = "; ".join(self.authority_errors) or "runtime skill authority invalid"
        else:
            self.phase = GovernancePhase.ORCHESTRATOR_REQUIRED

    @property
    def mode(self) -> GovernanceMode:
        if not self.governed:
            return GovernanceMode.HEALTHY
        if not self.authority_valid:
            return GovernanceMode.DEGRADED_READ_ONLY
        if self.phase in {GovernancePhase.ROUTER_FAILED, GovernancePhase.DECOMPOSER_FAILED,
                          GovernancePhase.MANDATORY_SKILL_MISSING, GovernancePhase.MANDATORY_SKILL_RESOLUTION_FAILED,
                          GovernancePhase.MANDATORY_SKILL_LOAD_FAILED, GovernancePhase.MANDATORY_GATE_ORDER_INVALID}:
            return GovernanceMode.DEGRADED_READ_ONLY
        return GovernanceMode.HEALTHY

    @property
    def downstream_allowed(self) -> bool:
        return self.governed and self.authority_valid and self.phase is GovernancePhase.GOVERNANCE_PREREQUISITES_PASSED

    @property
    def blocked(self) -> bool:
        return self.governed and not self.downstream_allowed

    def before_tool(self, tool_name: str, args: Mapping[str, Any] | None) -> GovernanceDecision:
        with self._lock:
            if not self.governed:
                return GovernanceDecision(True)
            args = dict(args or {})
            capability = classify_tool_capability(tool_name, args)
            try:
                spec = classify_operation(tool_name, args)
            except UnknownCapabilityError:
                spec = None

            if spec is not None and spec.side_effect_level == 0:
                policy_args = dict(args)
                if "allowed_roots" not in policy_args:
                    roots = list((self.bootstrap_packet or {}).get("route", {}).get("write_forbidden_roots", []))
                    if self.canonical_repo:
                        roots.append(self.canonical_repo)
                    if not roots:
                        roots.append(os.getcwd())
                    if roots:
                        policy_args["allowed_roots"] = roots
                if tool_name in {"codegraph_query", "codegraph_explore"} and "project_path" not in policy_args and self.canonical_repo:
                    policy_args["project_path"] = self.canonical_repo
                policy = evaluate_read_only(tool_name, policy_args)
                if policy.decision in {ReadOnlyDecision.ALLOW, ReadOnlyDecision.ALLOW_WITH_REDACTION}:
                    return GovernanceDecision(True)
                return GovernanceDecision(False, self._hard_receipt(policy.decision.value, policy.reason, tool_name, args))

            if spec is None and capability is ToolCapability.READ_ONLY:
                return GovernanceDecision(False, self._hard_receipt("BLOCK_UNKNOWN_TOOL", self.failure_reason, tool_name, args))

            if capability in {ToolCapability.EXTERNAL_MUTATION, ToolCapability.FINANCIAL,
                              ToolCapability.PLAY, ToolCapability.DEPLOYMENT, ToolCapability.DESTRUCTIVE,
                              ToolCapability.UNKNOWN}:
                return GovernanceDecision(False, self._hard_receipt(capability.value, self.failure_reason, tool_name, args))

            if self.native_workflow and self.bootstrap_packet:
                allowed = self.bootstrap_packet.get("allowed_tools", [])
                if tool_name not in allowed:
                    return GovernanceDecision(False, self._hard_receipt("TOOL_NOT_IN_BOOTSTRAP_ALLOWLIST", self.failure_reason, tool_name, args))
            if self.mode is GovernanceMode.DEGRADED_READ_ONLY:
                if capability in {ToolCapability.READ_ONLY, ToolCapability.LOCAL_ENGINEERING_WRITE}:
                    return GovernanceDecision(True)
                return GovernanceDecision(False, self._hard_receipt("GOVERNED_AUTHORITY_DEGRADED", self.failure_reason, tool_name, args))
            if self.downstream_allowed:
                return GovernanceDecision(True)
            return GovernanceDecision(False, self._workflow_receipt(tool_name, args))

    def observe_skill_result(self, requested_name: str, result: Mapping[str, Any] | None) -> None:
        with self._lock:
            if not self.governed or self.downstream_allowed:
                return
            expected = MANDATORY_SKILLS.get(self.phase)
            if expected is None or requested_name != expected[1]:
                return
            data = dict(result or {})
            success = data.get("success") is True
            resolved = data.get("skill_name") or data.get("name")
            self.observed.append({"gate": expected[0], "expected": expected[1], "requested": requested_name,
                                  "resolved": resolved, "success": success})
            if not success:
                self.failure_reason = str(data.get("error") or "skill resolution/load failed")
                self.phase = GovernancePhase.ROUTER_FAILED if expected[0] in {"entry", "0"} else GovernancePhase.DECOMPOSER_FAILED
                return
            if resolved and resolved != requested_name:
                self.failure_reason = f"resolved skill '{resolved}' differs from '{requested_name}'"
                self.phase = GovernancePhase.MANDATORY_SKILL_RESOLUTION_FAILED
                return
            self.phase = (GovernancePhase.ROUTER_REQUIRED if expected[0] == "entry"
                          else GovernancePhase.DECOMPOSER_REQUIRED if expected[0] == "0"
                          else GovernancePhase.GOVERNANCE_PREREQUISITES_PASSED)

    def _authority_receipt(self, capability: ToolCapability) -> str:
        return json.dumps({"error": "governed_authority_degraded", "governance": {
            "mode": GovernanceMode.DEGRADED_READ_ONLY.value, "capability": capability.value,
            "authority_errors": list(self.authority_errors), "downstream_execution_allowed": False,
            "reason": self.failure_reason or "relevant governed skill authority invalid",
        }}, ensure_ascii=False)

    def _hard_receipt(self, reason: str, reason_detail: str = "", tool_name: str | None = None,
                      args: Mapping[str, Any] | None = None) -> str:
        payload = {
            "status": "BLOCKED",
            "reason_code": reason,
            "hard_block": True,
            "state": self.phase.value,
            "detail": reason_detail,
            "tool": tool_name,
            "retry_other_tools": False,
            "next_action": None,
            "error": "governed_authority_degraded" if not self.authority_valid else "governed_mission_blocked",
            "governance": {"downstream_execution_allowed": False, "reason": reason_detail or reason},
        }
        return json.dumps(payload, ensure_ascii=False)

    def _workflow_receipt(self, tool_name: str, args: Mapping[str, Any]) -> str:
        fingerprint = json.dumps({"phase": self.phase.value, "tool": tool_name, "args": dict(args)}, sort_keys=True, default=str)
        count = self._denial_fingerprints.get(fingerprint, 0) + 1
        self._denial_fingerprints[fingerprint] = count
        if count >= 3:
            return json.dumps({
                "status": "BLOCKED",
                "reason_code": "WORKFLOW_CONVERGENCE_STOP",
                "hard_block": True,
                "state": self.phase.value,
                "repeat_count": count,
                "retry_other_tools": False,
                "next_action": None,
            }, ensure_ascii=False)
        next_action = {"tool": "skill_view", "arguments": {"name": ORCHESTRATOR}}
        if self.phase is GovernancePhase.ROUTER_REQUIRED:
            next_action = {"tool": "skill_view", "arguments": {"name": "lah-repo-router"}}
        elif self.phase is GovernancePhase.DECOMPOSER_REQUIRED:
            next_action = {"tool": "skill_view", "arguments": {"name": "mission-decomposer"}}
        return json.dumps({
            "status": "GUIDED",
            "reason_code": "WORKFLOW_PREREQUISITE_REQUIRED",
            "hard_block": False,
            "state": self.phase.value,
            "repeat_count": count,
            "retry_other_tools": False,
            "next_action": next_action,
        }, ensure_ascii=False)

    def _receipt(self, reason: str, gate: str | None = None, observed: Any = None) -> str:
        expected = MANDATORY_SKILLS.get(self.phase)
        gates = []
        if expected:
            gates.append({"gate": expected[0], "skill": expected[1], "status": "BLOCKED",
                          "observed": observed, "reason": self.failure_reason or reason})
        for item in self.observed:
            gates.append({"gate": item["gate"], "skill": item["expected"], "status": "PASS" if item["success"] else "FAIL"})
        return json.dumps({"error": "governed_mission_blocked", "governance": {
            "phase": self.phase.value, "required_gates": gates,
            "downstream_execution_allowed": False, "reason": self.failure_reason or reason,
        }}, ensure_ascii=False)
