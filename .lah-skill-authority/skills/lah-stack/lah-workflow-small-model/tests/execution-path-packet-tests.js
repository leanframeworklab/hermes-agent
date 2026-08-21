"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");

const {
  CertifiedExecutionPathPacket,
  compileCertifiedExecutionPathPacket,
  classifyDiscoveryAction,
  enforceDiscoveryAction,
  normalizeReadOnlyDecomposerResult,
  DISCOVERY_LEVEL,
  REDISCOVERY_BLOCKED,
  UNNECESSARY_SOURCE_ARCHAEOLOGY_BLOCKED,
} = require("../scripts/certified-execution-path-packet");

const context = {
  facts: {
    REPO_OWNERSHIP: {
      value: { canonical_checkout: "/workspace/canonical-repo" },
      source_authority: "router-receipt",
      staleness_policy: "never_stale_without_contradiction",
    },
    CAMPAIGN_EXECUTION_PATH: {
      value: { path: ["router", "compiler", "launcher", "provider"] },
      source_authority: "execution-receipt",
      staleness_policy: "never_stale_without_contradiction",
    },
    COMPILER_AUTHORITY: {
      value: { canonical_file: "services/campaign-compiler.js" },
      source_authority: "compiler-receipt",
      staleness_policy: "never_stale_without_contradiction",
    },
    P2_EXTERNAL_ACTION_BOUNDARY: {
      value: { canonical_file: "services/action-commit.js" },
      source_authority: "p2-receipt",
      staleness_policy: "never_stale_without_contradiction",
    },
  },
};

const resume = {
  mission_id: "READ_ONLY_FAST_CAMPAIGN_FIXTURE",
  current_checkpoint: "P2_READ_ONLY",
  next_action: "READ_CANONICAL_MAPPING",
  known_facts: { fixture: "read-only" },
  blocking_unknowns: [],
  forbidden_rediscovery: ["REPO_OWNERSHIP", "COMPILER_AUTHORITY"],
};

function packet() {
  return compileCertifiedExecutionPathPacket({
    context,
    resume,
    canonical_repo: "/workspace/canonical-repo",
    canonical_runtime_repo: "/workspace/hermes-runtime",
  });
}

test("T01_PACKET_FROM_CONTEXT_AND_RESUME", () => {
  const result = packet();
  assert.ok(result instanceof CertifiedExecutionPathPacket);
  assert.equal(result.mission_id, resume.mission_id);
  assert.equal(result.next_action, resume.next_action);
  assert.ok(result.known_execution_paths.some((entry) => entry.symbol === "COMPILER_AUTHORITY"));
});

test("T02_KNOWN_PATH_NO_SEARCH", () => {
  const result = classifyDiscoveryAction({ type: "find", target: "services/campaign-compiler.js" }, packet());
  assert.equal(result.level, DISCOVERY_LEVEL.PACKET);
  assert.equal(result.search_allowed, false);
});

test("T03_KNOWN_RELATIONSHIP_NO_CODEGRAPH", () => {
  const result = classifyDiscoveryAction({ type: "codegraph", relationship: "CAMPAIGN_EXECUTION_PATH" }, packet());
  assert.equal(result.level, DISCOVERY_LEVEL.PACKET);
  assert.equal(result.search_allowed, false);
});

test("T04_UNKNOWN_RELATIONSHIP_CODEGRAPH", () => {
  const result = classifyDiscoveryAction({ type: "relationship", relationship: "unknown-edge" }, packet());
  assert.equal(result.level, DISCOVERY_LEVEL.CODEGRAPH);
  assert.equal(result.preferred_method, "targeted_codegraph_relationship_query");
});

test("T05_CODEGRAPH_MISS_ALLOWS_BOUNDED_SEARCH", () => {
  const result = classifyDiscoveryAction(
    { type: "relationship", relationship: "unknown-edge" },
    packet(),
    { codegraph_miss: true, reason: "PACKET_MISS" },
  );
  assert.equal(result.level, DISCOVERY_LEVEL.BOUNDED_FILESYSTEM);
  assert.equal(result.search_allowed, true);
});

test("T06_CERTIFIED_REDISCOVERY_BLOCKED", () => {
  const result = enforceDiscoveryAction({ type: "find", target: "services/campaign-compiler.js" }, packet());
  assert.equal(result.error, REDISCOVERY_BLOCKED);
  assert.equal(result.classification, REDISCOVERY_BLOCKED);
});

test("T07_DIRECT_READ_REDIRECTION", () => {
  const result = enforceDiscoveryAction(
    { type: "freshness", target: "services/campaign-compiler.js" },
    packet(),
  );
  assert.equal(result.action.type, "direct_read");
  assert.equal(result.level, DISCOVERY_LEVEL.DIRECT_READ);
});

test("T08_READ_ONLY_DECOMPOSER_FALLBACK", () => {
  const result = normalizeReadOnlyDecomposerResult({
    mission_type: "READ_ONLY_AUDIT",
    result: { error: "Phase gate6_tests depends on unknown phase: gate5b_implementation", plan: null },
  });
  assert.equal(result.classification, "DECOMPOSER_FALLBACK_READ_ONLY");
  assert.equal(result.gate, "SATISFIED_BY_DOCUMENTED_FALLBACK");
});

test("T09_UNKNOWN_DECOMPOSER_FAILURE_BLOCKED", () => {
  const result = normalizeReadOnlyDecomposerResult({
    mission_type: "READ_ONLY_AUDIT",
    result: { error: "unexpected parser failure" },
  });
  assert.equal(result.blocked, true);
  assert.equal(result.classification, "DECOMPOSER_FAILURE_BLOCKED");
});

test("T10_NEXT_ACTION_DIRECT_EXECUTION", () => {
  const result = packet().nextActionDecision();
  assert.deepEqual(result, { classification: "DIRECT_EXECUTION", next_action: resume.next_action });
});

test("T11_BLOCKING_UNKNOWN_CAN_DISCOVER", () => {
  const result = compileCertifiedExecutionPathPacket({
    context,
    resume: { ...resume, blocking_unknowns: ["missing relationship"] },
  }).nextActionDecision();
  assert.equal(result.classification, "TARGETED_DISCOVERY_REQUIRED");
});

test("T12_NO_DUPLICATE_GOVERNANCE_LAYER", () => {
  const source = fs.readFileSync(path.join(__dirname, "../scripts/certified-execution-path-packet.js"), "utf8");
  assert.match(source, /CertifiedArchitectureContext|context/);
  assert.doesNotMatch(source, /class .*Governor|class .*StateMachine/);
});

test("T13_DANGEROUS_ACTION_FAIL_CLOSED", () => {
  const result = enforceDiscoveryAction({ type: "PLAY", target: "provider" }, packet());
  assert.equal(result.allowed, false);
  assert.equal(result.reason, "DANGEROUS_ACTION_FAIL_CLOSED");
});

test("T14_P1_P2_P3_REGRESSION", () => {
  assert.equal(typeof require("../scripts/mission-resume-packet").MissionResumePacket, "function");
  assert.equal(typeof require("../scripts/certified-architecture-context").CertifiedArchitectureContext, "function");
  assert.equal(typeof require("../scripts/convergence-governor").ConvergenceGovernor, "function");
});

test("bounded filesystem search requires packet and CodeGraph misses", () => {
  const result = classifyDiscoveryAction({ type: "find", target: "unknown" }, packet(), { codegraph_miss: false });
  assert.equal(result.error, UNNECESSARY_SOURCE_ARCHAEOLOGY_BLOCKED);
});
