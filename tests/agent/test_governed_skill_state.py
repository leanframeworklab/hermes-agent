import json

from agent.governed_skill_state import (
    GovernancePhase,
    GovernedSkillState,
    GovernanceMode,
    classify_governed_mission,
)


def test_explicit_lah_workflow_turn_requires_orchestrator_then_dependencies():
    assert classify_governed_mission("/lah-workflow MISSION: audit repo") is True
    state = GovernedSkillState(governed=True)

    assert state.before_tool("skill_view", {"name": "lah-workflow-small-model"}).allowed
    state.observe_skill_result("lah-workflow-small-model", {"success": True})
    assert state.before_tool("skill_view", {"name": "lah-repo-router"}).allowed
    state.observe_skill_result("lah-repo-router", {"success": True})
    assert state.phase is GovernancePhase.DECOMPOSER_REQUIRED

    assert state.before_tool("skill_view", {"name": "mission-decomposer"}).allowed
    state.observe_skill_result("mission-decomposer", {"success": True})
    assert state.downstream_allowed is True


def test_malformed_router_cannot_satisfy_gate():
    state = GovernedSkillState(governed=True)
    decision = state.before_tool("skill_view", {"name": "lah-stack/lah-repo-router"})
    assert decision.allowed is False
    assert state.phase is GovernancePhase.ORCHESTRATOR_REQUIRED
    assert json.loads(decision.result)["reason_code"] == "BLOCK_PATH_ESCAPE"


def test_failed_router_blocks_downstream_and_decomposer():
    state = GovernedSkillState(governed=True)
    state.observe_skill_result("lah-workflow-small-model", {"success": True})
    state.observe_skill_result("lah-repo-router", {"success": False, "error": "missing"})

    for name in ("mission-decomposer", "terminal", "write_file"):
        decision = state.before_tool(
            "skill_view" if name == "mission-decomposer" else name,
            {"name": name} if name == "mission-decomposer" else {},
        )
        if name in {"mission-decomposer", "write_file"}:
            assert decision.allowed is True
        else:
            assert decision.allowed is False
            assert json.loads(decision.result)["governance"]["downstream_execution_allowed"] is False


def test_router_bootstrap_failure_keeps_read_only_recovery_available():
    state = GovernedSkillState(governed=True)
    state.observe_skill_result("lah-workflow-small-model", {"success": True})
    state.observe_skill_result("lah-repo-router", {"success": False, "error": "router unavailable"})

    assert state.mode is GovernanceMode.DEGRADED_READ_ONLY
    assert state.before_tool("read_file", {"path": "agent/tool_executor.py"}).allowed
    assert state.before_tool("provider_update", {}).allowed is False


def test_non_lah_turn_is_unaffected():
    assert classify_governed_mission("Explain Python decorators") is False
    state = GovernedSkillState(governed=False)
    assert state.before_tool("terminal", {"command": "true"}).allowed


def test_invalid_critical_authority_blocks_governed_turn():
    state = GovernedSkillState(
        governed=True,
        authority_valid=False,
        authority_errors=("lah-repo-router: content drift",),
    )
    assert state.downstream_allowed is False
    assert state.before_tool("terminal", {}).allowed is False


def test_small_model_orchestrator_starts_before_internal_dependencies():
    state = GovernedSkillState(governed=True)

    assert state.before_tool(
        "skill_view", {"name": "lah-workflow-small-model"}
    ).allowed
    state.observe_skill_result(
        "lah-workflow-small-model",
        {"success": True, "skill_name": "lah-workflow-small-model"},
    )
    assert state.phase is GovernancePhase.ROUTER_REQUIRED

    assert state.before_tool("skill_view", {"name": "lah-repo-router"}).allowed
    state.observe_skill_result("lah-repo-router", {"success": True})
    assert state.before_tool("skill_view", {"name": "mission-decomposer"}).allowed
    state.observe_skill_result("mission-decomposer", {"success": True})
    assert state.mode is GovernanceMode.HEALTHY


def test_invalid_authority_enters_read_only_degraded_mode():
    state = GovernedSkillState(
        governed=True,
        authority_valid=False,
        authority_errors=("lah-workflow-small-model: content drift",),
    )

    assert state.mode is GovernanceMode.DEGRADED_READ_ONLY
    assert state.before_tool("read_file", {"path": "agent/governed_skill_state.py"}).allowed
    assert json.loads(state.before_tool("codegraph_query", {"query": "GovernanceMode"}).result)["reason_code"] == "BLOCK_PATH_ESCAPE"
    assert state.before_tool("terminal", {"command": "git status --short"}).allowed


def test_invalid_relevant_authority_blocks_mutation_without_label_bypass():
    state = GovernedSkillState(
        governed=True,
        authority_valid=False,
        authority_errors=("lah-workflow-small-model: runtime fingerprint mismatch",),
    )

    decision = state.before_tool(
        "provider_update",
        {"campaign_id": "8557556", "capability": "READ_ONLY"},
    )
    assert decision.allowed is False
    payload = json.loads(decision.result)
    assert payload["error"] == "governed_authority_degraded"
    assert payload["governance"]["downstream_execution_allowed"] is False


def test_certified_routing_allows_read_only_codegraph_without_manual_router():
    state = GovernedSkillState(
        governed=True,
        certified_routing_established=True,
        canonical_repo="/home/deploy/hermes-agent",
    )

    assert state.before_tool("codegraph_query", {"query": "known"}).allowed
    assert state.before_tool("codegraph_explore", {"query": "relationship"}).allowed


def test_certified_routing_does_not_bypass_dangerous_actions():
    state = GovernedSkillState(
        governed=True,
        certified_routing_established=True,
        canonical_repo="/home/deploy/hermes-agent",
    )

    assert state.before_tool("provider_update", {}).allowed is False
    assert state.before_tool("campaign_play", {}).allowed is False
