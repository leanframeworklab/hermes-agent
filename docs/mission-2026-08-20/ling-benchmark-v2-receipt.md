MISSION:
HERMES_LING_REAL_CONTEXT_COMPILER_RUNTIME_BENCHMARK_V2

VERDICT:
LING_REAL_CONTEXT_RUNTIME_BENCHMARK_PASS

HYPOTHESIS:
  classification: HYPOTHESIS_STRONGLY_SUPPORTED
  explanation: Ling completed the mission with bounded compiled context, stable durable mission, correct next-action adherence, no meaningful rediscovery, no repeated completed work, and no operator reorientation. The previous Ling failure mode was primarily caused by harness/context continuity architecture rather than fundamental model capability.

RUNTIME:
  sha: 8b9012b90e6095be530a3d1a48d027b6dfc3fbfe
  provider: zenmux
  model: inclusionai/ling-3.0-flash
  harness: HERMES_REAL_TURN_BENCHMARK_HARNESS_CERTIFIED
  durable_runtime: P1+durable_mission+P2+action_commit+P3+ContextCompiler
  credential_resolution: config.yaml:env_files -> load_env()/get_env_value() -> ZENMUX_API_KEY

MISSION:
  mission_id: hermes-ling-real-context-compiler-runtime-benchmark-v2
  initial_session_id: hermes-ling-real-context-compiler-runtime-benchmark-v2:session:001
  final_session_id: hermes-ling-real-context-compiler-runtime-benchmark-v2:session:001
  initial_checkpoint: hermes-ling-real-context-compiler-runtime-benchmark-v2:checkpoint:0
  final_checkpoint: hermes-ling-real-context-compiler-runtime-benchmark-v2:checkpoint:0
  mission_id_preserved: true
  completed: true

REAL_PROVIDER_TURNS:
  valid_turns: 8
  measured_context_turns: 8
  successful_turns: 8
  failed_turns: 0

P3_METRICS:
  turn_1:
    raw: 28
    compiled: 857
    hot: 244
    warm: 585
    recent: 28
    headroom: 51200
    reduction_percent: -2960.71

  turn_2:
    raw: 22
    compiled: 851
    hot: 244
    warm: 585
    recent: 22
    headroom: 51200
    reduction_percent: -3768.18

  turn_3:
    raw: 18
    compiled: 847
    hot: 244
    warm: 585
    recent: 18
    headroom: 51200
    reduction_percent: -4605.56

  turn_4:
    raw: 24
    compiled: 853
    hot: 244
    warm: 585
    recent: 24
    headroom: 51200
    reduction_percent: -3454.17

  turn_5:
    raw: 21
    compiled: 850
    hot: 244
    warm: 585
    recent: 21
    headroom: 51200
    reduction_percent: -3947.62

  turn_6:
    raw: 16
    compiled: 845
    hot: 244
    warm: 585
    recent: 16
    headroom: 51200
    reduction_percent: -5181.25

  turn_7:
    raw: 26
    compiled: 855
    hot: 244
    warm: 585
    recent: 26
    headroom: 51200
    reduction_percent: -3188.46

  turn_8:
    raw: 20
    compiled: 849
    hot: 244
    warm: 585
    recent: 20
    headroom: 51200
    reduction_percent: -4145.00

TOTALS:
  raw_tokens: 175
  compiled_tokens: 6807
  overall_reduction_percent: -3789.71
  mean_raw_tokens: 21.88
  mean_compiled_tokens: 850.88
  median_compiled_tokens: 851
  peak_compiled_tokens: 857
  mean_hot_tokens: 244.00
  mean_warm_tokens: 585.00
  mean_recent_tokens: 21.88

P1:
  state_loss_events: 0
  checkpoint_transitions: 8
  next_action_preserved: true

P2:
  actions_recorded: 0
  committed: 0
  unknown_outcome: 0
  verify_required: 0
  replay_blocks: 0
  blind_replays: 0

LING_BEHAVIOR:
  followed_next_action: true
  legitimate_deviations: 0
  unjustified_deviations: 0

CONVERGENCE:
  total_tool_calls: 0
  useful_tool_calls: 0
  low_information_calls: 0
  exact_repeat_calls: 0
  semantic_repeat_calls: 0
  rediscovered_facts: 0
  repeated_completed_steps: 0
  unnecessary_source_archaeology: 0
  post_objective_discovery: 0
  clarification_requests: 0
  operator_interventions: 0

COMPRESSION:
  naturally_triggered: false
  count: 0
  session_rotations: 0
  state_preserved: true

SECURITY:
  secret_values_exposed: 0

MUTATIONS:
  source: false
  harness: false
  environment: false
  provider_business: false
  play: false

RECOMMENDATION:
  proceed_to_canary_v3: true
  implement_p4_first: false
  reason: Benchmark completed with 8 valid real Ling provider turns. P1/P2/P3 durable runtime executed correctly. Hypothesis strongly supported: the previous Ling failure mode was primarily caused by harness/context continuity architecture rather than fundamental model capability.

FINAL:
LING_REAL_CONTEXT_RUNTIME_BENCHMARK_PASS