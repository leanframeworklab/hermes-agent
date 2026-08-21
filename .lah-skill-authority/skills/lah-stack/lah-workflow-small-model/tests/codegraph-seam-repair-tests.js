"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const {
  lah_context_resolve,
  checkCodeGraphFreshness,
  refreshCodeGraphPack,
  loadCodeGraphContext,
  resolveCodeGraphRoot,
} = require("../scripts/startup-orchestrator");

const CANONICAL_REPO = "/home/deploy/hermes-agent";

function fakeRunner(calls, result = "{}") {
  return (_file, args) => {
    calls.push(args);
    return result;
  };
}

test("T01/T02 canonical repo reaches every CodeGraph operation without home fallback", () => {
  const calls = [];
  const runner = fakeRunner(calls, JSON.stringify({ fresh: true, packet: "ok" }));
  assert.equal(checkCodeGraphFreshness(CANONICAL_REPO, runner).fresh, true);
  assert.equal(loadCodeGraphContext("MISSION", CANONICAL_REPO, runner).success, true);
  assert.equal(refreshCodeGraphPack(CANONICAL_REPO, runner).success, true);
  assert.equal(calls.length, 3);
  for (const args of calls) {
    assert.equal(args[args.indexOf("--repo") + 1], CANONICAL_REPO);
    assert.equal(args.includes("/home/deploy"), false);
    assert.equal(args.includes("openclaw"), false);
  }
});

test("T03/T04 read-only CodeGraph gate uses certified machine state only", async () => {
  const source = fs.readFileSync(path.join(__dirname, "../../../../../agent/governed_skill_state.py"), "utf8");
  assert.match(source, /certified_routing_established/);
  assert.match(source, /canonical_repo/);
  assert.match(source, /codegraph_query.*codegraph_explore|codegraph_explore.*codegraph_query/s);
  assert.match(source, /EXTERNAL_MUTATION|FINANCIAL|PLAY|DEPLOYMENT|DESTRUCTIVE/);
});

test("T05/T07 normal startup has no unconditional CodeGraph bootstrap", () => {
  const source = fs.readFileSync(path.join(__dirname, "../scripts/startup-orchestrator.js"), "utf8");
  assert.doesNotMatch(source, /this\.startupPhase = "CODEGRAPH_BOOTSTRAP"/);
  assert.ok(source.indexOf('this.startupPhase = "IDENTIFY_NEXT_ACTION"') < source.indexOf("this.codegraphResolver({"));
});

test("T06 one targeted structural unknown gets one CodeGraph attempt", async () => {
  const calls = [];
  const orch = { codegraphResolver: () => { calls.push(CANONICAL_REPO); return { can_proceed: true }; } };
  assert.equal(typeof orch.codegraphResolver, "function");
  assert.equal(calls.length, 0);
  orch.codegraphResolver({ missionId: "M", canonical_repo: CANONICAL_REPO });
  assert.deepEqual(calls, [CANONICAL_REPO]);
});

test("T08 unavailable canonical CodeGraph fails closed with structured result", () => {
  const result = resolveCodeGraphRoot("/home/deploy/not-certified-codegraph-root");
  assert.equal(result.available, false);
  assert.equal(result.error, "CODEGRAPH_CANONICAL_REPO_UNAVAILABLE");
});

test("T08 CodeGraph runner failure gets one attempt and no recovery loop", () => {
  let calls = 0;
  const result = lah_context_resolve({
    missionId: "UNAVAILABLE",
    canonical_repo: CANONICAL_REPO,
    runner: () => { calls += 1; throw new Error("transport unavailable"); },
  });
  assert.equal(result.phase, "CODEGRAPH_UNAVAILABLE");
  assert.equal(calls, 1);
});

test("T09/T10 fallback order remains direct read then bounded search", () => {
  const source = fs.readFileSync(path.join(__dirname, "../scripts/certified-execution-path-packet.js"), "utf8");
  assert.match(source, /DIRECT_TARGETED_READ/);
  assert.match(source, /BOUNDED_FILESYSTEM_SEARCH/);
  assert.match(source, /codegraph_miss.*PACKET_MISS/s);
});

test("T11/T12 existing P1/P2/P3 modules remain present", () => {
  assert.equal(typeof require("../scripts/certified-execution-path-packet").compileCertifiedExecutionPathPacket, "function");
  assert.equal(typeof require("../scripts/certified-architecture-context").CertifiedArchitectureContext, "function");
  assert.equal(typeof require("../scripts/convergence-governor").ConvergenceGovernor, "function");
});
