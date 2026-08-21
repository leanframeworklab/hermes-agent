"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const {
  classifyCodegraphIntent,
  buildCodegraphInvocation,
} = require("./codegraph-primitive-selection.cjs");

const symbol = "compileCertifiedExecutionPathPacket";

test("precise caller question selects callers primitive", () => {
  const intent = classifyCodegraphIntent(
    `What function/method calls ${symbol} from the startup path?`,
  );
  assert.deepEqual(intent, { kind: "caller", target: symbol, primitive: "callers" });
  assert.deepEqual(buildCodegraphInvocation(intent), ["callers", symbol]);
  assert.equal(classifyCodegraphIntent(`does startup call ${symbol}?`).primitive, "callers");
});

test("exact symbol lookup selects query", () => {
  assert.equal(classifyCodegraphIntent(`locate exact symbol ${symbol}`).primitive, "query");
});

test("callee, impact, affected, and broad intents select matching primitives", () => {
  assert.equal(classifyCodegraphIntent(`what does ${symbol} call?`).primitive, "callees");
  assert.equal(classifyCodegraphIntent(`impact of changing ${symbol}`).primitive, "impact");
  assert.equal(classifyCodegraphIntent("which tests are affected by changed source files").primitive, "affected");
  assert.equal(classifyCodegraphIntent("explore the broad architecture across modules").primitive, "explore");
});
