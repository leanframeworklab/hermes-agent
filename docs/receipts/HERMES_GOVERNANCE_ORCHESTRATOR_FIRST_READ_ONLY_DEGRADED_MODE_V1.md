# HERMES_GOVERNANCE_ORCHESTRATOR_FIRST_READ_ONLY_DEGRADED_MODE_V1

## VERDICT

HERMES_GOVERNANCE_SIMPLIFIED_AND_CERTIFIED

## BASELINE

- branch: `hermes-skill-governance-final-v1`
- starting_sha: `f13431a60615b0aa4f91fc143b7f0b94604b55a5`
- implementation_sha: `d79631ec0c`
- runtime launcher: `/home/deploy/.local/bin/hermes`
- resolved launcher: `/home/deploy/hermes-agent/venv/bin/hermes`
- runtime source binding: `/home/deploy/.hermes/skills/lah-stack/lah-workflow-small-model/SKILL.md`
- starting authority: invalid; `lah-workflow-small-model` declared runtime fingerprint mismatch and content drift
- final worktree: clean after receipt commit
- unrelated dirty work preserved: true; primary checkout untouched

## ROOT_CAUSE

- dependency_inversion: `GovernedSkillState.__post_init__` initialized every governed turn at `ROUTER_REQUIRED`; `before_tool()` denied all non-router calls, making router and decomposer external prerequisites.
- global_lockout: failed mandatory resolution and invalid authority returned `governed_mission_blocked` with `downstream_execution_allowed=false` for every tool class.
- fingerprint_failure_blast_radius: one critical skill error propagated through `turn_context.py` into shared governed dispatch.
- recovery_path_before: no bounded read-only recovery; authority failure poisoned governed dispatch before diagnosis.

## ARCHITECTURE_DECISION

- governed_skill_state: `KEEP_AND_NARROW`
- rationale: it remains the single owning boundary for orchestrator bootstrap sequencing and capability policy; it no longer duplicates dangerous-action guards or globally blocks diagnostics.

## ORCHESTRATOR_FIRST

- direct_invocation: true; initial governed phase is `ORCHESTRATOR_REQUIRED`.
- router_internal: true; router follows successful orchestrator observation.
- decomposer_internal: true; decomposer follows successful router observation.
- manual_preload_required: false.

## DEGRADED_MODE

- state: `HEALTHY`, `DEGRADED_READ_ONLY`, `BLOCKED_DANGEROUS_ACTION` semantic model; authority and bootstrap failures enter `DEGRADED_READ_ONLY`.
- read_only_available: true.
- codegraph_available: true through explicit read-only capability classification.
- diagnostics_available: true through skill inspection, file/search inspection, safe terminal reads, and existing runtime authority validation.
- dangerous_external_mutations_blocked: true.

## FINGERPRINT_AUTHORITY

- validation_preserved: true; source/runtime fingerprints, manifest, invocation identity, and provenance checks unchanged.
- global_lockout_removed: true; invalid authority no longer blocks read-only or local engineering-write capabilities.
- affected_authority_fail_closed: true; external mutation, financial, PLAY, deployment, destructive, and unknown capabilities fail closed during degradation.
- generated_artifact_follow_up: governed source tree contains durable receipts/docs while runtime tree differs; fingerprint churn remains a follow-up defect, not redesigned here.

## SAFETY

- play: preserved; no PLAY execution.
- financial: preserved; no policy or cap changes.
- provider_mutation: blocked during degraded authority; no provider call.
- approvals: unchanged; no approval mutation.
- replay: P2 tests pass; committed actions are not replayed and verification boundaries remain intact.
- deployment: unchanged; no deployment request.

## TESTS

- focused: `111 passed, 1 warning` across authority, governed state/dispatch, degraded-mode, durable mission, action commit, and context compiler tests.
- adversarial: drift, runtime fingerprint mismatch, missing manifest entry, malformed identity, router failure, forged READ_ONLY label, safe terminal allowlist all covered.
- p1: `tests/agent/test_durable_mission.py` passed.
- p2: `tests/agent/test_action_commit.py` passed.
- p3: `tests/agent/test_context_compiler.py` passed.
- canonical: router `validate-routing-drift.cjs` returned `DRIFT_CHECK_PASS`.
- real_failures: broad agent suite had 41 unrelated pre-existing failures; changed-file focused slice had zero failures.
- infrastructure_blocked: system pytest lacked timeout plugin; ACP tests lacked `acp`; broad suite had socket permission errors and provider/LSP/network environment failures. Router fixture scripts failed independently on installed fixture/JSON behavior.

## INVARIANTS

```
ORCHESTRATOR_FIRST=true
READ_ONLY_DEGRADED_MODE=true
FINGERPRINT_DRIFT_GLOBAL_TOOL_LOCKOUT=false
MANUAL_ROUTER_PRELOAD_REQUIRED=false
MANUAL_DECOMPOSER_PRELOAD_REQUIRED=false
DANGEROUS_MUTATIONS_FAIL_CLOSED=true
P1_PRESERVED=true
P2_PRESERVED=true
P3_PRESERVED=true
NO_PROVIDER_MUTATION=true
PLAY_EXECUTED=false
SECRET_VALUES_EXPOSED=0
```

## FOLLOW_UP_DEFECTS

- Generated receipts/docs inside governed skill source tree participate in `_skill_fingerprint`; source/runtime artifact topology should be normalized in a separate authority-maintenance mission.
- Installed router fixture tests need repair independently; no changes made here.

## SECURITY

- secret_values_exposed: 0
- campaign/business state changed: 0
- P4 added: 0

## FINAL

Implementation committed at `d79631ec0c`; receipt commit follows. No campaign canary, campaign resume, provider mutation, PLAY, deployment, or P4 work performed.
