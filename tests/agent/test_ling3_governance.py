import json
from pathlib import Path

import pytest

from agent.ling3_bootstrap import compile_bootstrap_packet
from agent.read_only_policy import ReadOnlyDecision, evaluate_read_only
from agent.side_effect_registry import UnknownCapabilityError, classify_operation
from agent.governed_skill_state import GovernedSkillState
from agent.tool_executor import _governance_preflight
from tools.pure_calculation_tool import PureCalculationError, pure_calculation


def test_level_zero_read_is_not_blocked_by_workflow_prerequisites(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text("skill", encoding="utf-8")
    state = GovernedSkillState(governed=True)

    decision = state.before_tool("read_file", {"path": str(path), "allowed_roots": [str(tmp_path)]})

    assert decision.allowed is True


def test_skill_view_is_safe_before_workflow_bootstrap():
    state = GovernedSkillState(governed=True)

    assert state.before_tool("skill_view", {"name": "lah-workflow"}).allowed is True


def test_unknown_operation_fails_closed():
    with pytest.raises(UnknownCapabilityError):
        classify_operation("unknown_tool", {})


def test_operation_level_registry_distinguishes_pure_calculation():
    assert classify_operation("pure_calculation", {}).side_effect_level == 0
    assert classify_operation("execute_code", {"mode": "pure_calculation"}).side_effect_level > 0
    assert classify_operation("execute_code", {"mode": "arbitrary"}).side_effect_level > 0


def test_path_escape_is_denied(tmp_path):
    decision = evaluate_read_only(
        "read_file",
        {"path": str(tmp_path / ".." / "secret.txt"), "allowed_roots": [str(tmp_path)]},
    )
    assert decision.decision == ReadOnlyDecision.BLOCK_PATH_ESCAPE


def test_symlink_escape_is_denied(tmp_path):
    outside = tmp_path.parent / "ling3-outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(outside)
    decision = evaluate_read_only(
        "read_file", {"path": str(link), "allowed_roots": [str(tmp_path)]}
    )
    assert decision.decision == ReadOnlyDecision.BLOCK_PATH_ESCAPE


def test_secret_read_requires_redaction(tmp_path):
    secret = tmp_path / ".env"
    secret.write_text("TOKEN=secret", encoding="utf-8")
    blocked = evaluate_read_only(
        "read_file", {"path": str(secret), "allowed_roots": [str(tmp_path)]}
    )
    redacted = evaluate_read_only(
        "read_file",
        {"path": str(secret), "allowed_roots": [str(tmp_path)], "redact": True},
    )
    assert blocked.decision == ReadOnlyDecision.BLOCK_SECRET
    assert redacted.decision == ReadOnlyDecision.ALLOW_WITH_REDACTION


def test_pure_calculation_rejects_forbidden_capabilities():
    decision = evaluate_read_only(
        "pure_calculation", {"sandbox_profile": "pure_calculation_v1", "code": "import os; print(os.getenv('X'))", "limits": {"cpu_operations": 100, "memory_bytes": 131072, "output_chars": 4096, "wall_time_ms": 2000}}
    )
    assert decision.decision == ReadOnlyDecision.BLOCK_HIDDEN_MUTATION


def test_pure_calculation_handler_is_bounded_and_side_effect_free():
    limits = {"cpu_operations": 100, "memory_bytes": 131072, "output_chars": 4096, "wall_time_ms": 2000}
    assert pure_calculation("2 + 2 * 3", limits)["value"] == 8
    with pytest.raises(PureCalculationError):
        pure_calculation("__import__('os')", limits)


def test_bootstrap_compiles_math_without_codegraph_or_decomposition():
    packet = compile_bootstrap_packet(
        mission_id="math-1",
        mission_text="perform bounded mathematical certification",
        initial_action={"tool": "pure_calculation", "arguments": {"sandbox_profile": "pure_calculation_v1", "code": "2+2", "limits": {"cpu_operations": 100, "memory_bytes": 131072, "output_chars": 4096, "wall_time_ms": 2000}}},
    )
    assert packet["schema_version"] == "lah-ling3-bootstrap-v1"
    assert packet["problem_family"] == "MATH_CERTIFICATION"
    assert packet["requirements"]["codegraph"] == "UNNECESSARY"
    assert packet["requirements"]["decomposition"] == "BYPASS"
    assert packet["next_action"]["tool"] in packet["allowed_tools"]


def test_bootstrap_requires_codegraph_for_structural_repair():
    packet = compile_bootstrap_packet(
        mission_id="repair-1",
        mission_text="repair a cross-module code defect",
    )
    assert packet["problem_family"] == "CODE"
    assert packet["requirements"]["codegraph"] == "REQUIRED"


def test_bootstrap_requires_decomposition_for_multi_repo_scope():
    packet = compile_bootstrap_packet(
        mission_id="multi-1",
        mission_text="diagnose runtime and repository integration",
        route={"decision": "RESOLVED", "repository_authority": "repo-a", "context_repos": ["repo-b"]},
        acceptance_gates=2,
    )
    assert packet["requirements"]["decomposition"] == "REQUIRED"


def test_bootstrap_marks_provider_mutation_as_hard_blocked():
    packet = compile_bootstrap_packet(
        mission_id="provider-1",
        mission_text="provider mutation mission stopped at authorization",
    )
    assert packet["side_effect_level"] == 4
    assert "OPERATOR_APPROVAL_REQUIRED" in packet["hard_blockers"]


def test_bootstrap_rejects_next_action_outside_allowlist():
    with pytest.raises(ValueError, match="next_action.tool"):
        compile_bootstrap_packet(
            mission_id="bad-1",
            mission_text="read one known file",
            initial_action={"tool": "unknown_tool", "arguments": {}},
        )


def test_workflow_denial_converges_without_alternate_tool_guidance():
    state = GovernedSkillState(governed=True)
    first = json.loads(state.before_tool("write_file", {"path": "x"}).result)
    second = json.loads(state.before_tool("write_file", {"path": "x"}).result)
    third = json.loads(state.before_tool("write_file", {"path": "x"}).result)

    assert first["status"] == "GUIDED"
    assert second["repeat_count"] == 2
    assert third["reason_code"] == "WORKFLOW_CONVERGENCE_STOP"
    assert third["retry_other_tools"] is False


def test_dispatch_preflight_allows_safe_read_before_bootstrap(tmp_path):
    path = tmp_path / "known.txt"
    path.write_text("ok", encoding="utf-8")

    class Agent:
        _governed_skill_state = GovernedSkillState(governed=True)

    assert _governance_preflight(
        Agent(), "read_file", {"path": str(path), "allowed_roots": [str(tmp_path)]}
    ) is None


def test_validated_managed_skill_root_allows_exact_read_without_explicit_root(tmp_path, monkeypatch):
    managed_root = tmp_path / "skills"
    skill_file = managed_root / "lah-stack" / "lah-workflow-ling3" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("---\nname: lah-workflow-ling3\n---\n", encoding="utf-8")
    monkeypatch.setattr("tools.skill_authority.get_hermes_home", lambda: tmp_path)

    state = GovernedSkillState(governed=True, authority_valid=True)

    assert state.before_tool("read_file", {"path": str(skill_file)}).allowed is True


def test_managed_skill_root_does_not_allow_secret_or_sibling_paths(tmp_path, monkeypatch):
    managed_root = tmp_path / "skills"
    safe_file = managed_root / "lah-stack" / "lah-workflow-ling3" / "SKILL.md"
    safe_file.parent.mkdir(parents=True)
    safe_file.write_text("safe", encoding="utf-8")
    secret_file = managed_root / ".env"
    secret_file.write_text("TOKEN=synthetic", encoding="utf-8")
    sibling = tmp_path / ".hermes" / ".env"
    sibling.parent.mkdir()
    sibling.write_text("outside", encoding="utf-8")
    monkeypatch.setattr("tools.skill_authority.get_hermes_home", lambda: tmp_path)

    state = GovernedSkillState(governed=True, authority_valid=True)

    secret = json.loads(state.before_tool("read_file", {"path": str(secret_file)}).result)
    outside_state = GovernedSkillState(governed=True, authority_valid=True)
    outside = json.loads(outside_state.before_tool("read_file", {"path": str(sibling)}).result)
    assert secret["reason_code"] == "BLOCK_SECRET"
    assert outside["reason_code"] == "BLOCK_PATH_ESCAPE"


def test_hard_path_denial_does_not_poison_unrelated_terminal_evaluation(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    state = GovernedSkillState(governed=True)

    first = json.loads(state.before_tool("read_file", {"path": str(outside), "allowed_roots": [str(tmp_path)]}).result)
    second = json.loads(state.before_tool("terminal", {"command": "cat /tmp/outside.txt"}).result)

    assert first["reason_code"] == "BLOCK_PATH_ESCAPE"
    assert second["reason_code"] == "BLOCK_UNKNOWN_TOOL"
    assert second["scope"] == "ACTION"
    assert second["hard_block"] is True
    assert second["retry_other_tools"] is False


def _calc_args(code="2 + 2"):
    return {
        "sandbox_profile": "pure_calculation_v1",
        "code": code,
        "limits": {
            "cpu_operations": 100,
            "memory_bytes": 131072,
            "output_chars": 4096,
            "wall_time_ms": 2000,
        },
    }


def test_denied_terminal_does_not_poison_exact_read(tmp_path):
    path = tmp_path / "evidence.txt"
    path.write_text("evidence", encoding="utf-8")
    state = GovernedSkillState(governed=True)

    denied = json.loads(state.before_tool("terminal", {"command": "cat /tmp/evidence.txt"}).result)
    allowed = state.before_tool("read_file", {"path": str(path), "allowed_roots": [str(tmp_path)]})

    assert denied["scope"] == "ACTION"
    assert denied["mission_still_valid"] is True
    assert allowed.allowed is True


def test_denied_execute_code_does_not_poison_pure_calculation():
    state = GovernedSkillState(governed=True)

    denied = json.loads(state.before_tool("execute_code", {"code": "2 + 2"}).result)
    allowed = state.before_tool("pure_calculation", _calc_args())

    assert denied["scope"] == "ACTION"
    assert denied["blocked_capability_family"] == "GENERAL_EXECUTION"
    assert allowed.allowed is True


def test_terminal_equivalent_bypass_converges_only_within_family(tmp_path):
    path = tmp_path / "evidence.txt"
    path.write_text("evidence", encoding="utf-8")
    state = GovernedSkillState(governed=True)

    first = json.loads(state.before_tool("terminal", {"command": "cat /tmp/evidence.txt"}).result)
    second = json.loads(state.before_tool("execute_code", {"code": "open('/tmp/evidence.txt').read()"}).result)
    allowed = state.before_tool("read_file", {"path": str(path), "allowed_roots": [str(tmp_path)]})

    assert first["scope"] == "ACTION"
    assert second["reason_code"] == "WORKFLOW_CONVERGENCE_STOP"
    assert second["scope"] == "ACTION"
    assert second["blocked_capability_family"] == "FILE_BYPASS"
    assert allowed.allowed is True


def test_ling3_native_bootstrap_clears_legacy_orchestrator_state():
    packet = compile_bootstrap_packet(
        mission_id="ling3-1",
        mission_text="READ_ONLY_ANALYTICAL use lah-workflow-ling3",
        initial_action={"tool": "skill_view", "arguments": {"name": "lah-workflow-ling3"}},
    )
    state = GovernedSkillState(governed=True, bootstrap_packet=packet, native_workflow=True)

    assert state.phase.name == "GOVERNANCE_PREREQUISITES_PASSED"
    assert state.before_tool("skill_view", {"name": "lah-workflow-ling3"}).allowed is True
    state.observe_skill_result("lah-workflow-ling3", {"success": True, "skill_name": "lah-workflow-ling3"})
    assert state.phase.name == "GOVERNANCE_PREREQUISITES_PASSED"
    assert state.before_tool("skill_view", {"name": "lah-repo-router"}).allowed is True
    assert state.before_tool("read_file", {"path": __file__, "allowed_roots": [str(tmp_path := Path(__file__).parent)]}).allowed is True


def test_true_authority_failure_is_mission_blocked():
    state = GovernedSkillState(
        governed=True,
        authority_valid=False,
        authority_errors=("runtime authority invalid",),
    )

    payload = json.loads(state.before_tool("terminal", {"command": "git status --short"}).result)

    assert payload["scope"] == "MISSION"
    assert payload["mission_still_valid"] is False
