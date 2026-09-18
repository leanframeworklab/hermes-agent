# HERMES_P1_P3_REAL_TURN_BENCHMARK_HARNESS_FIX_V1

VERDICT: HERMES_REAL_TURN_BENCHMARK_HARNESS_CERTIFIED

BASELINE:
  branch: hermes-dashboard-recovery-v1
  starting_sha: 8b9012b90e6095be530a3d1a48d027b6dfc3fbfe
  final_sha: 8b9012b90e6095be530a3d1a48d027b6dfc3fbfe
  clean: false

ROOT_CAUSE:
  p1_binding: old benchmark omitted session_db, session_id, and mission_id
  p3_metrics: old step_callback ran before provider and counted API iterations as turns
  classification: BENCHMARK_HARNESS_BUG

FILES_CHANGED:
  - tests/helpers/durable_benchmark.py
  - tests/helpers/test_durable_benchmark.py
  - docs/mission-2026-08-20/harness-fix-receipt.md

P1_BENCHMARK_BINDING:
  implementation: SessionDB.create_session, create_mission, write_mission_checkpoint
  session_binding: verified
  checkpoint_creation: ACTIVE checkpoint verified
  restore_success: verified

P3_METRICS_REFRESH:
  update_boundary: build_turn_context after ContextCompiler.compile
  per_turn: read after run_conversation returns
  stale_before: true
  stale_after: false
  compiled_tokens_gt_zero: true
  hot_tokens_gt_zero: true

BENCHMARK_HARNESS:
  location: tests/helpers/
  core_runtime_changes_required: false
  private_attribute_access_required: false
  source_archaeology_required: false

FAKE_PROVIDER_INTEGRATION:
  turns: 2
  mission_preserved: true
  checkpoint_progression: true
  turn1_metrics: raw=14 compiled>0 hot>0
  turn2_metrics: fresh object compiled>0 hot>0

REAL_LING_SMOKE:
  credential_available: true
  provider: zenmux
  model: inclusionai/ling-3.0-flash
  real_turns: 2
  durable_mission_active: true
  checkpoints_active: true
  metrics_turns: 2
  turn1_metrics: raw=14 compiled=815 hot=216
  turn2_metrics: raw=14 compiled=818 hot=219
  compiled_tokens_gt_zero: true
  hot_tokens_gt_zero: true
  mission_id_preserved: true
  metrics_fresh: true
  provider_turns_confirmed: true

TESTS:
  focused: 98 passed
  p1: passed
  p2: passed
  p3: passed
  telemetry: passed
  canonical: 351 passed; 3 pytest-asyncio infrastructure failures
  real_failures: 0 in changed scope
  blocked_infrastructure: pytest-asyncio unavailable; one pre-existing stale MagicMock fixture failure in run_agent tests

SECURITY:
  secret_values_exposed: 0
  secret_preflight: passed

BUSINESS_PROVIDER_MUTATION:
  false

PLAY_EXECUTED:
  false

BENCHMARK_READY:
  true

NEXT_MISSION:
  HERMES_LING_REAL_CONTEXT_COMPILER_RUNTIME_BENCHMARK_V1

FINAL:
  HERMES_REAL_TURN_BENCHMARK_HARNESS_CERTIFIED
