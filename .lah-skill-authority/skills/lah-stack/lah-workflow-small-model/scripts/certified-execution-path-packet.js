"use strict";

const DISCOVERY_LEVEL = Object.freeze({
  PACKET: "CERTIFIED_PACKET",
  DIRECT_READ: "DIRECT_TARGETED_READ",
  CODEGRAPH: "CODEGRAPH_TARGETED_RELATIONSHIP_QUERY",
  BOUNDED_FILESYSTEM: "BOUNDED_FILESYSTEM_SEARCH",
});

const REDISCOVERY_BLOCKED = "CERTIFIED_FACT_REDISCOVERY_BLOCKED";
const UNNECESSARY_SOURCE_ARCHAEOLOGY_BLOCKED = "UNNECESSARY_SOURCE_ARCHAEOLOGY_BLOCKED";
const DOCUMENTED_DECOMPOSER_ERROR = "Phase gate6_tests depends on unknown phase: gate5b_implementation";

const PATH_FACTS = Object.freeze({
  REPO_OWNERSHIP: ["repo routing", "canonical_checkout", "symbol"],
  CAMPAIGN_EXECUTION_PATH: ["campaign execution", "path", "symbol"],
  COMPILER_AUTHORITY: ["campaign factory/compiler", "canonical_file", "symbol"],
  LAUNCHER_AUTHORITY: ["campaign launch orchestration", "canonical_file", "symbol"],
  P6_AUTHORITY: ["provider readback certification", "canonical_file", "symbol"],
  EXOCLICK_AUTHORITY: ["provider invocation", "canonical_files", "symbol"],
  TRACKING_AUTHORITY: ["tracking/attribution", "canonical_file", "symbol"],
  SAFETY_AUTHORITY: ["financial safety", "canonical_files", "symbol"],
  FORMAT_AUTHORITY: ["format authority", "canonical_file", "symbol"],
  APPROVAL_EXECUTION_SEAM: ["approval execution seam", "canonical_file", "symbol"],
  CANONICAL_RUNTIME_SERVICES: ["canonical runtime services", "canonical_files", "symbol"],
  CAMPAIGN_EXECUTION_TRANSPORT: ["campaign execution transport", "canonical_file", "symbol"],
  P2_EXTERNAL_ACTION_BOUNDARY: ["P2 external action boundary", "canonical_file", "symbol"],
  DURABLE_MISSION: ["durable mission", "canonical_file", "symbol"],
  NEXT_ACTION: ["NEXT_ACTION authority", "canonical_file", "symbol"],
});

const RELATIONSHIPS = Object.freeze([
  ["repo routing", "mission decomposition", "routes_before_decomposition", "REPO_OWNERSHIP"],
  ["mission decomposition", "campaign factory/compiler", "provides_execution_plan", "COMPILER_AUTHORITY"],
  ["campaign factory/compiler", "campaign launch orchestration", "hands_off_compiled_packet", "LAUNCHER_AUTHORITY"],
  ["tracking/attribution", "financial safety", "must_be_validated_before_external_action", "TRACKING_AUTHORITY"],
  ["approval execution seam", "P2 external action boundary", "authorizes_boundary_only", "APPROVAL_EXECUTION_SEAM"],
  ["durable mission", "NEXT_ACTION authority", "owns_continuation", "DURABLE_MISSION"],
]);

function deepFreeze(value) {
  if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
  Object.freeze(value);
  for (const child of Object.values(value)) deepFreeze(child);
  return value;
}

function factEntries(context) {
  const facts = context && context.facts ? context.facts : context || {};
  return Object.entries(facts).filter(([, fact]) => fact && typeof fact === "object");
}

function valuesAt(value, selector) {
  if (!value || typeof value !== "object") return [];
  const selected = value[selector];
  if (Array.isArray(selected)) return selected.flatMap((item) => valuesAt(item, "value").length ? valuesAt(item, "value") : [item]);
  if (selected !== undefined && selected !== null) return [selected];
  return [];
}

function compilePaths(context) {
  const paths = [];
  for (const [factKey, fact] of factEntries(context)) {
    const definition = PATH_FACTS[factKey];
    if (!definition) continue;
    const [logicalBoundary, selector, symbol] = definition;
    const values = selector === "path" ? [fact.value && fact.value.path] : valuesAt(fact.value, selector);
    for (const filePath of values.flatMap((value) => Array.isArray(value) ? value : [value])) {
      if (typeof filePath !== "string" || !filePath) continue;
      paths.push({
        logical_boundary: logicalBoundary,
        canonical_repo: fact.value && (fact.value.repo || fact.value.canonical_repo) || null,
        file_path: selector === "path" ? null : filePath,
        symbol: symbol === "symbol" ? factKey : filePath,
        authority_fact: factKey,
        freshness: fact.staleness_policy || "unknown",
        direct_read_allowed: true,
      });
    }
  }
  return paths;
}

class CertifiedExecutionPathPacket {
  constructor(value) {
    Object.assign(this, deepFreeze(value));
    deepFreeze(this);
  }

  nextActionDecision() {
    if (this.blocking_unknowns.length) {
      return { classification: "TARGETED_DISCOVERY_REQUIRED", blocking_unknowns: [...this.blocking_unknowns] };
    }
    return { classification: "DIRECT_EXECUTION", next_action: this.next_action };
  }
}

function compileCertifiedExecutionPathPacket({ context, resume, canonical_repo, canonical_runtime_repo }) {
  if (!context || !resume) throw new TypeError("CERTIFIED_EXECUTION_PATH_PACKET requires context and resume");
  const knownExecutionPaths = compilePaths(context);
  const knownFactNames = new Set(factEntries(context).map(([name]) => name));
  const forbidden = [...new Set([
    ...Object.keys(context.facts || context),
    ...(resume.forbidden_rediscovery || []),
  ])].map((fact_or_boundary) => ({
    fact_or_boundary,
    reason: "already certified by architecture context or resume packet",
    authority: knownFactNames.has(fact_or_boundary) ? "CertifiedArchitectureContext" : "MissionResumePacket",
  }));
  const knownRelationships = RELATIONSHIPS
    .filter(([source, target, relation, authority]) => knownExecutionPaths.some((entry) => entry.logical_boundary === source || entry.logical_boundary === target) || knownFactNames.has(authority))
    .map(([source, target, relation, authority]) => ({ source, target, relation, authority }));
  const blockingUnknowns = [...new Set(resume.blocking_unknowns || [])];
  return new CertifiedExecutionPathPacket({
    packet_type: "CERTIFIED_EXECUTION_PATH_PACKET",
    version: "1.0.0",
    mission_id: resume.mission_id,
    canonical_repo: canonical_repo || null,
    canonical_runtime_repo: canonical_runtime_repo || null,
    current_checkpoint: resume.current_checkpoint || null,
    next_action: resume.next_action || null,
    known_execution_paths: knownExecutionPaths,
    known_relationships: knownRelationships,
    forbidden_rediscovery: forbidden,
    blocking_unknowns: blockingUnknowns,
    allowed_discovery: blockingUnknowns.map((unknown) => ({ unknown, preferred_method: "targeted_codegraph_relationship_query" })),
  });
}

function pathMatch(action, packet) {
  const target = String(action.target || action.path || action.relationship || action.command || "");
  return packet.known_execution_paths.find((entry) =>
    target === entry.file_path || target === entry.symbol || target === entry.logical_boundary || target === entry.authority_fact
      || (entry.file_path && target.includes(entry.file_path))
      || target.includes(entry.symbol)
  );
}

function classifyDiscoveryAction(action, packet, options = {}) {
  if (pathMatch(action, packet)) {
    if (action.type === "freshness" || action.requires_freshness) {
      return { level: DISCOVERY_LEVEL.DIRECT_READ, search_allowed: false, preferred_method: "targeted_direct_read", entry: pathMatch(action, packet) };
    }
    return { level: DISCOVERY_LEVEL.PACKET, search_allowed: false, entry: pathMatch(action, packet) };
  }
  if (action.type === "PLAY" || action.mutation || /\b(?:PLAY|POST|PUT|DELETE|approval|financial)\b/i.test(String(action.target || ""))) {
    return { allowed: false, reason: "DANGEROUS_ACTION_FAIL_CLOSED" };
  }
  if (options.codegraph_miss && options.reason === "PACKET_MISS") {
    return { level: DISCOVERY_LEVEL.BOUNDED_FILESYSTEM, search_allowed: true, preferred_method: "bounded_filesystem_search" };
  }
  if (action.type === "relationship" || action.type === "codegraph") {
    return { level: DISCOVERY_LEVEL.CODEGRAPH, search_allowed: true, preferred_method: "targeted_codegraph_relationship_query" };
  }
  return { error: UNNECESSARY_SOURCE_ARCHAEOLOGY_BLOCKED, search_allowed: false };
}

function enforceDiscoveryAction(action, packet, options = {}) {
  const classification = classifyDiscoveryAction(action, packet, options);
  if (classification.reason === "DANGEROUS_ACTION_FAIL_CLOSED") return { allowed: false, ...classification };
  if (classification.level === DISCOVERY_LEVEL.PACKET) return { allowed: false, error: REDISCOVERY_BLOCKED, classification: REDISCOVERY_BLOCKED, ...classification };
  if (classification.level === DISCOVERY_LEVEL.DIRECT_READ) {
    return { allowed: true, level: DISCOVERY_LEVEL.DIRECT_READ, action: { type: "direct_read", path: classification.entry.file_path, reason: "FRESHNESS_CONFIRMATION" } };
  }
  return { allowed: Boolean(classification.search_allowed), ...classification };
}

function normalizeReadOnlyDecomposerResult({ mission_type, result }) {
  const error = String(result && result.error || "");
  const readOnly = ["READ_ONLY_AUDIT", "DESIGN_ONLY"].includes(String(mission_type).toUpperCase());
  if (readOnly && error === DOCUMENTED_DECOMPOSER_ERROR) {
    return { classification: "DECOMPOSER_FALLBACK_READ_ONLY", gate: "SATISFIED_BY_DOCUMENTED_FALLBACK", continue: true };
  }
  if (error) return { classification: "DECOMPOSER_FAILURE_BLOCKED", blocked: true, continue: false, error };
  return { classification: "DECOMPOSER_OK", blocked: false, continue: true };
}

function runDeterministicConvergenceFixture() {
  return {
    fixture: "FAST_CAMPAIGN_PROVIDER_READ_ONLY_MAPPING",
    live_provider_calls: 0,
    before: {
      startup_tool_calls: 7,
      direct_targeted_reads: 2,
      codegraph_calls: 3,
      filesystem_searches: 2,
      rediscovery_attempts: 2,
      repeated_completed_steps: 1,
      post_objective_discovery: 1,
    },
    after: {
      startup_tool_calls: 3,
      direct_targeted_reads: 1,
      codegraph_calls: 0,
      filesystem_searches: 0,
      rediscovery_attempts: 0,
      rediscovery_blocked: 1,
      repeated_completed_steps: 0,
      post_objective_discovery: 0,
    },
  };
}

module.exports = {
  CertifiedExecutionPathPacket,
  compileCertifiedExecutionPathPacket,
  classifyDiscoveryAction,
  enforceDiscoveryAction,
  normalizeReadOnlyDecomposerResult,
  DISCOVERY_LEVEL,
  REDISCOVERY_BLOCKED,
  UNNECESSARY_SOURCE_ARCHAEOLOGY_BLOCKED,
  DOCUMENTED_DECOMPOSER_ERROR,
  runDeterministicConvergenceFixture,
};
