"use strict";

const PRIMITIVES = new Set(["query", "node", "callers", "callees", "impact", "affected", "explore"]);

function extractTarget(text) {
  const candidates = String(text).match(/[A-Za-z_$][A-Za-z0-9_$]*/g) || [];
  return candidates.filter((candidate) =>
    /[a-z_$]/.test(candidate) && (/[A-Z]/.test(candidate) || candidate.length > 12)
  ).sort((a, b) => b.length - a.length)[0] || null;
}

function classifyCodegraphIntent(text) {
  const source = String(text || "");
  const target = extractTarget(source);
  if (/\b(affected|which tests|which files).*(changed|change|modified|source)/i.test(source) ||
      /\b(changed|modified)\s+(source\s+)?files?\b/i.test(source)) {
    return { kind: "affected", target, primitive: "affected" };
  }
  if (/\b(impact|blast radius|downstream effects?)\b/i.test(source)) {
    return { kind: "impact", target, primitive: "impact" };
  }
  if (/\b(callee|callees|what does .+ call|what does .+ invoke|outbound calls?)\b/i.test(source)) {
    return { kind: "callee", target, primitive: "callees" };
  }
  if (/\b(caller|callers|who calls|what invokes|does .+ call|invokes? .+ from|calls .+ from)\b/i.test(source)) {
    return { kind: "caller", target, primitive: "callers" };
  }
  if (/\b(exact symbol|symbol lookup|locate|where is|source|trail|direct source)\b/i.test(source) && target) {
    return { kind: "symbol", target, primitive: /\b(source|trail|direct source)\b/i.test(source) ? "node" : "query" };
  }
  return { kind: "exploration", target: null, primitive: "explore" };
}

function buildCodegraphInvocation(intent, query = intent.target) {
  if (!intent || !PRIMITIVES.has(intent.primitive)) throw new TypeError("Unsupported CodeGraph primitive");
  if (intent.primitive === "explore") return ["explore", JSON.stringify(query)];
  if (!intent.target) throw new TypeError(`CodeGraph ${intent.primitive} requires a target`);
  return [intent.primitive, intent.target];
}

module.exports = { classifyCodegraphIntent, buildCodegraphInvocation };
