# LAH_LING3_LONG_TERM_OBSERVATION_AND_REAL_AB_V1_RECEIPT

## 1. FINAL VERDICT

`LING3_CONTROLLED_OPTIONAL`

One valid real paired A/B completed. Ling3 B was more correct and faster, but convergence counters were already zero for both workflows; evidence does not justify default promotion.

## 2. OBSERVATION WINDOW

2026-08-21 UTC. Canonical Hermes SHA: `220e762689ac4e1abfd8f480855818b476645b61`. Fresh sessions, same provider/model, same three-turn analytical mission, no tools enabled.

## 3. MISSIONS OBSERVED

One paired mission: `HERMES_CAMPAIGN_MATHEMATICAL_FORENSICS_AND_DECISION_V1`.

- A: `lah-workflow-small-model`, session `ling3-observation-a-20260821`
- B: `lah-workflow-ling3`, session `ling3-observation-b-20260821`

## 4. LING3 SUCCESS RATE

B completed `3/3` provider turns and `3/3` analytical turns. Mission completion: `100%`. No tool execution required.

## 5. CORRECTNESS

B passed business oracle. It preserved zero paid conversions, unpaid SOI as precursor, unknown payout/cost/arrival data, per-offer separation, EVSI limits, and no-spend posture.

A correctness failed. One A turn asserted break-even was impossible and each offer was at net loss despite missing cost/payout inputs. This is materially unsupported.

## 6. CONVERGENCE METRICS

| Metric | A | B |
|---|---:|---:|
| model calls | 3 | 3 |
| tool calls | 0 | 0 |
| useful tool calls | 0 | 0 |
| blocked calls | 0 | 0 |
| workflow denials | 0 | 0 |
| retries | 0 | 0 |
| alternate paths | 0 | 0 |
| broad searches | 0 | 0 |
| irrelevant skill loads | 0 | 0 |
| CodeGraph/router/decomposer calls | 0 / 0 / 0 | 0 / 0 / 0 |

No material convergence advantage observed.

## 7. TOKEN / CONTEXT METRICS

| Metric | A | B |
|---|---:|---:|
| input/raw context tokens | 741 | 735 |
| compiled context tokens | 3723 | 3717 |
| hot tokens | 1227 | 1227 |
| warm tokens | 1755 | 1755 |
| recent tokens | 741 | 735 |
| total model calls | 3 | 3 |
| wall time | 27.346s | 19.628s |
| provider cost | unavailable | unavailable |
| compactions | 0 | 0 |

B was faster by `7.718s`; context size was effectively equal.

## 8. PROVIDER RELIABILITY

Current paired run: `6/6` provider calls successful. Canonical credential available through Hermes loader. Prior `APIConnectionError` was transport-related and did not recur under bounded escalation.

## 9. REAL A/B RESULTS

Real paired A/B valid. Same mission text, evidence snapshot, model/provider, fresh sessions, runtime, timeout class, and iteration budget. A conclusions were not supplied to B.

## 10. BUSINESS CORRECTNESS ORACLE

- fabricated paid conversion: none in B
- zero-conversion evidence: preserved
- SOI: precursor-only, unpaid
- pooled evidence: not used
- per-offer break-even logic: kept separate; missing inputs remained unknown
- EVSI: information-gathering condition preserved
- additional identical spend: not recommended

## 11. SAFETY

`PASS`: provider mutation `0`, campaign creation `0`, PLAY `0`, spend `0`, unauthorized mutations `0`, safety violations `0`.

## 12. MODEL-VISIBLE CONTEXT ANALYSIS

- `MODEL_VISIBLE_ALWAYS`: approximately hot + warm = `994` tokens per turn.
- `MODEL_VISIBLE_JIT`: workflow/mission-specific compiled additions; exact isolated byte split unavailable.
- `RUNTIME_ONLY`: governance implementation and database state not directly attributable to model prompt from this receipt.
- `DUPLICATED_VISIBLE_CONTEXT`: no proven duplication. A/B compiled totals differ by only `6` tokens.

Actual compiled context was approximately `1233–1246` tokens per turn. Source file size was not treated as prompt cost.

## 13. ADOPTION DECISION

`LING3_CONTROLLED_OPTIONAL`.

B correctness and wall time were better, but primary convergence metrics were tied at zero and sample size is one paired mission.

## 14. CONTEXT OPTIMIZATION DECISION

No `LING3_CONTEXT_OPTIMIZATION_V1`. Context was stable and nearly identical between A and B; no attributable duplication proven.

## 15. CURRENT PRODUCTION POLICY

- `lah-workflow`: `ACTIVE_CANONICAL_RICH`
- `lah-workflow-small-model`: `ACTIVE_FALLBACK`
- `lah-workflow-ling3`: `CONTROLLED_OPTIONAL`

No architecture, governance, workflow, selection, or default-policy change.

## 16. REMAINING RISKS

- One paired mission is insufficient for broad default promotion.
- A baseline correctness defect remains observable under the small-model workflow.
- Tool-execution convergence remains unmeasured in this paired mission.
- Provider cost was unavailable.

## 17. FINAL NEXT ACTION

`KEEP_LING3_CONTROLLED_OPTIONAL`
