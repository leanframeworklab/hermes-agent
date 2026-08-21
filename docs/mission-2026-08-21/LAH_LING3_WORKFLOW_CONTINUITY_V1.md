# LAH Ling3 Workflow Continuity V1

## OBSERVATIONS

- Canonical Hermes SHA `3daf2857d3d22971025b65e3644b711d7cf4b36a` active in source checkout.
- Current deterministic C3 matrix passed with exact expected blockers and `0` safety violations.
- Offline proxy B removed retries and alternate paths, but did not reduce tokens.
- Real ZenMux attempt failed at transport with `APIConnectionError` before valid A/B evidence.

## DECISIONS

- C3 certified.
- D benchmark inconclusive.
- E adoption remains `LING3_CONTROLLED_OPTIONAL`.
- No workflow selection change.
- No old workflow deleted.

## CERTIFIED FACTS

- `lah-workflow-ling3` consumes `lah-ling3-bootstrap-v1`.
- Level-0 math and exact reads can execute directly.
- Path, unknown-tool, hidden-mutation, provider, PLAY, spend, and destructive boundaries fail closed.

## REJECTED APPROACHES

- No universal rollout without real A/B evidence.
- No token optimization before paired benchmark.
- No cleanup of dirty or unmerged worktrees.
- No provider mutation, campaign creation, PLAY, spend, or deletion.

## CURRENT DEFAULT POLICY

`lah-workflow` remains canonical-rich. `lah-workflow-small-model` remains fallback. Ling3 remains controlled optional.

## OPEN RISKS

- Provider transport availability.
- Dependency skew between `.venv` and system pytest.
- Unmeasured direct model-visible permanent context.

## NEXT ORIENTATIONS

Run real same-mission A/B after provider recovery; collect business correctness oracle and context metrics.
