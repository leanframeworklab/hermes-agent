import json

from agent.governed_skill_state import GovernedSkillState
from agent.tool_executor import _governance_preflight


class _Agent:
    def __init__(self):
        self._governed_skill_state = GovernedSkillState(
            governed=True,
            authority_valid=False,
            authority_errors=("lah-repo-router: declared source fingerprint mismatch",),
        )


def test_drift_keeps_diagnostics_and_codegraph_available():
    agent = _Agent()

    assert _governance_preflight(agent, "skill_view", {"name": "lah-repo-router"}) is None
    assert _governance_preflight(agent, "skills_list", {}) is None
    assert _governance_preflight(agent, "search_files", {"query": "ROUTER_REQUIRED"}) is None
    assert _governance_preflight(agent, "codegraph_query", {"query": "tool dispatch"}) is None


def test_drift_blocks_external_mutation_with_authority_receipt():
    agent = _Agent()

    blocked = _governance_preflight(
        agent,
        "campaign_provider_mutate",
        {"operation": "update", "capability": "READ_ONLY"},
    )
    assert blocked is not None
    payload = json.loads(blocked)
    assert payload["error"] == "governed_authority_degraded"
    assert "fingerprint" in payload["governance"]["reason"]


def test_drift_allows_conservative_read_only_terminal_command():
    agent = _Agent()
    assert _governance_preflight(agent, "terminal", {"command": "git diff -- agent"}) is None
    assert _governance_preflight(agent, "terminal", {"command": "git status --short"}) is None
    assert _governance_preflight(agent, "terminal", {"command": "git add agent"}) is not None
