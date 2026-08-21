"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const {
  runDeterministicConvergenceFixture,
  compileCertifiedExecutionPathPacket,
} = require("../scripts/certified-execution-path-packet");
const { ConvergenceGovernor } = require("../scripts/convergence-governor");

test("startup builds packet before NEXT_ACTION and uses CodeGraph only after decision", () => {
  const source = fs.readFileSync(path.join(__dirname, "../scripts/startup-orchestrator.js"), "utf8");
  assert.ok(source.indexOf('"BUILD_CERTIFIED_EXECUTION_PATH_PACKET"') < source.indexOf('this.startupPhase = "IDENTIFY_NEXT_ACTION"'));
  assert.ok(source.indexOf('this.startupPhase = "IDENTIFY_NEXT_ACTION"') < source.indexOf("this.codegraphResolver({"));
});

test("convergence governor consumes packet at dispatch boundary", () => {
  const packet = compileCertifiedExecutionPathPacket({
    context: { facts: { COMPILER_AUTHORITY: { value: { canonical_file: "services/compiler.js" } } } },
    resume: { mission_id: "fixture", current_checkpoint: "P2", next_action: "READ", blocking_unknowns: [], forbidden_rediscovery: [] },
  });
  const governor = new ConvergenceGovernor({ certifiedExecutionPathPacket: packet });
  const result = governor.recordAction({ command: "grep compiler services/compiler.js", mode: "READ_ONLY_AUDIT" });
  assert.equal(result.error, "CERTIFIED_FACT_REDISCOVERY_BLOCKED");
});

test("deterministic convergence fixture meets token and discovery targets", () => {
  const result = runDeterministicConvergenceFixture();
  assert.equal(result.after.startup_tool_calls <= 3, true);
  assert.equal(result.after.filesystem_searches, 0);
  assert.equal(result.after.rediscovery_attempts, 0);
  assert.equal(result.after.rediscovery_blocked >= 1, true);
  assert.equal(result.after.codegraph_calls, 0);
  assert.equal(result.live_provider_calls, 0);
});
