---
name: lah-workflow-small-model
description: "Compact gated LAH Stack workflow for small/fast models (Ling 3 Flash, etc.). Same role as lah-workflow; optimized for explicit decision boundaries, bounded discovery, certified runbook fast path, and strong STOP semantics. Do not modify lah-workflow."
---

# LAH Workflow — Small Model Variant

**Role:** Same as `lah-workflow` — tells Hermes how to behave on the LAH stack.

**Difference:** Execution style optimized for small/fast reasoning models. Every instruction is explicit, bounded, and deterministic. No implicit assumptions. No exploratory search by default.

**Does NOT modify** `lah-workflow`. The canonical skill is untouched.

---

## Authority Order

Resolve authority in this exact order. A lower-authority source must never override a higher-authority STOP.

1. **Current operator authorization** — explicit, current, governed
2. **Hard constraints** — Safety, financial, governance (non-negotiable)
3. **Certified mission runbook** — frozen artifact, loaded verbatim
4. **This workflow** (`lah-workflow-small-model`)
5. **Domain skill** — loaded only when the mission type requires it
6. **Generic tool behavior** — default tool semantics
7. **Historical receipts/logs** — reference only, never override current state

---

## Mission Mode Classification

Classify every mission into exactly ONE primary mode before executing. Do not silently switch modes.

| Mode | When | Behavior |
|------|------|----------|
| **EXECUTE** | Follow an existing certified runbook or canonical workflow | Minimal discovery. Mutations only when explicitly authorized. STOP after each step. |
| **DIAGNOSTIC** | Investigate a specific unresolved defect | Read-only unless escalated. Bounded investigation allowed. |
| **REPAIR** | Repair a confirmed defect | Root cause required before modification. Focused tests only. No scope expansion. |
| **CERTIFY** | Collect evidence and return a verdict | No repair. No architectural improvisation. No mutation unless certification explicitly requires a governed canary. |

If the mission genuinely requires another mode: **STOP** and request/reclassify explicitly.

---

## Certified Runbook Fast Path

When a certified mission runbook exists (e.g., `t03-certified-runbook`), this path takes priority over all workflow steps.

1. Load the certified runbook.
2. Validate its current required inputs and invariants.
3. Execute the next canonical step.
4. Collect only the evidence required by that step.
5. Return its receipt/verdict.
6. **STOP.**

Do not rediscover architecture unless the runbook explicitly enters DIAGNOSTIC mode.
Do not reconstruct the workflow from historical receipts, source code, or previous conversations.

---

## Search Budget (Anti-Archaeology)

Forbidden by default in EXECUTE and CERTIFY modes:

- Broad recursive grep
- Broad find
- Filesystem archaeology
- Worktree archaeology
- Port scanning
- Route guessing
- Reading unrelated implementation files
- Historical receipt archaeology
- Repeated searches for the same fact
- Constructing alternate execution paths
- Ad-hoc provider calls when canonical wrappers exist

Allowed narrow lookups only when required to resolve a named canonical artifact.

| Mode | Max discovery actions |
|------|----------------------|
| EXECUTE | 1 narrow lookup before STOP/UNRESOLVED |
| CERTIFY | 2 narrow evidence-resolution actions |
| DIAGNOSTIC | Bounded investigation (mission-scoped) |
| REPAIR | Bounded investigation around confirmed root cause |

---

## Evidence Contract

Use the correct evidence class for each assertion. Lower-class evidence cannot override higher-class evidence.

| Class | Requirement |
|-------|-------------|
| **RUNTIME STATE** | Prefer canonical health/state/readback. Source code is not runtime evidence. |
| **PROVIDER STATE** | Prefer canonical provider reader. Historical receipt is not current provider state. |
| **AUTHORIZATION** | Require current governed authorization evidence. Do not infer from budget or historical approval. |
| **SAFETY** | Require current Supervisor/Governor canonical state. Do not infer Safety state from implementation source. |
| **DEPLOYMENT** | Require actual runtime provenance. Git HEAD alone may be insufficient unless runtime is proven to execute that checkout. |
| **CERTIFIED HISTORY** | Use frozen certified artifacts for workflow semantics/history, not for current mutable state. |

---

## Stop Contract

When any STOP condition triggers, halt immediately. Do not improvise fallback paths.

| Condition | Action |
|-----------|--------|
| UNKNOWN_CANONICAL_STATE | BLOCKED_SAFE |
| CANONICAL_ROUTE_UNAVAILABLE | BLOCKED_SAFE |
| AUTHORIZATION_UNCLEAR | BLOCKED_SAFE |
| INDEPENDENT_BLOCKER | STOP |
| CERTIFICATION_FAILURE | RECERTIFICATION_REQUIRED |
| NEW_DEFECT_DURING_EXECUTE | STOP — do NOT silently switch to REPAIR |
| NEW_DEFECT_DURING_CERTIFY | STOP — do NOT repair |
| REPAIR_REQUIRES_SCOPE_EXPANSION | STOP |

---

## LCM Context Discipline

Optimize for Hermes LCM long-running sessions.

- Prefer compact facts over raw log replay.
- Do not reload full historical missions when a certified receipt/runbook exists.
- Do not paste large source files into working context unnecessarily.
- Preserve canonical IDs/hashes/verdicts exactly.
- Summarize completed phases into compact state.
- Do not repeatedly reconstruct already-certified facts.
- Treat frozen certified artifacts as references.
- Treat current runtime state as fresh evidence.

Internal working state (keep compact):

```
MODE
OBJECTIVE
CURRENT_STEP
REQUIRED_FACTS
FACTS_OBSERVED
BLOCKER
ALLOWED_ACTION
NEXT_ACTION
```

---

## Gate Sequence (Compact)

The canonical gate sequence from `lah-workflow` is preserved. Small-model execution uses the same gates but with tighter bounds:

1. **Gate 0** — Repo routing preflight (MANDATORY). Load `lah-repo-router`.
2. **Gate 0.5** — Mission decomposition (MANDATORY). Load `mission-decomposer`.
3. **Gate 1** — CodeGraph (resolved repo only, maxFiles: 12).
4. **Gate 2** — AutoResearch (read-only). Use `research` skill if needed.
5. **Gate 3** — Superpowers Plan. Use `grill-me`/`grill-with-docs` only if design is fuzzy.
6. **Gate 4** — FastSafe Gate (15 checks). Batch when possible.
7. **Gate 5** — Implementation (varies by mission type).
8. **Gate 6** — Tests & Verification.
9. **Gate 7** — Operator Packet.
10. **Gate 8** — Commit (ciblé staging, mission-code prefix).
11. **Gate 9** — PR & Merge.
12. **Gate 10** — Memory Lock.
13. **Gate 11** — Continuity JSON.

For mission-type specifics (READ_ONLY_AUDIT, DESIGN_ONLY, MIXED, PROMOTION_ONLY), consult `lah-workflow`. This small-model variant does not duplicate those branches — it defers to the canonical skill for mission-type branching logic.

---

## Sub-Agent Discipline

- `delegate_task` max 3 per call.
- For 4-6 lanes, split into 2 sequential batches.
- Each sub-agent gets: routing context, exact paths, safety invariants, expected output format.
- Sub-agents have zero access to parent memory.
- Do not spawn sub-agents for discovery-only work — use narrow lookup instead.

---

## Communication

Caveman levels by phase (loaded from `caveman` skill):

- **NORMAL** — routing preflight, arch/design/plan/risk (Gates 0-3)
- **LITE** — FastSafe, progress, operator tests, memory lock (Gates 4-6, 9.5, 10)
- **FULL** — tests, PR, merge, continuity (Gates 6-9, 11)
