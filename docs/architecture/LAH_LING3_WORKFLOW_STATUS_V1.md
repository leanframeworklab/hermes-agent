# LAH Ling3 Workflow Status V1

Current status: `CONTROLLED_OPTIONAL`.

`lah-workflow-ling3` is native and deterministic. It consumes a compiled `lah-ling3-bootstrap-v1` packet. Runtime owns capability classification, path safety, authorization, and convergence. Ling3 selects only packet-provided next actions; denial is terminal and does not trigger alternate-tool retries.

Permanent context contains the state model, packet contract, side-effect levels, safety invariants, stop semantics, and next-action rules. Problem-family references are JIT. CodeGraph and decomposition remain conditional, not universal.

Workflow status:

- `lah-workflow`: `ACTIVE_CANONICAL_RICH`
- `lah-workflow-small-model`: `ACTIVE_FALLBACK`
- `lah-workflow-ling3`: `CONTROLLED_OPTIONAL`

Adoption gate: C3 deterministic behavioral certification passed. Required real same-mission A/B benchmark remains inconclusive because the fresh provider run failed with `APIConnectionError`; therefore no default selection policy is active.

Safety policy: no campaign CREATE, PLAY, spend, provider mutation, deployment, deletion, or uncontrolled runtime mutation under this status.
