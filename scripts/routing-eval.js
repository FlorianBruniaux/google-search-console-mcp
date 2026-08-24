#!/usr/bin/env node
"use strict";

/**
 * Calibration report for the project routing corpus.
 *
 * Reuses the global router's own tokenizer and BM25 so the numbers here match
 * what bm25-suggest actually computes at runtime. Reads nothing from
 * ~/.claude/hooks/routing/data, so it can be run while the router rebuilds its
 * index without racing it.
 *
 *   node scripts/routing-eval.js            report every target
 *   node scripts/routing-eval.js <target>   drill into one target's collisions
 *
 * A target is healthy at f1 >= 0.6. Below that, build-index marks it "conflict"
 * and its suggestions are noise. The usual cause is two targets sharing a
 * sentence skeleton, not sharing a topic: rephrase one side, then add the
 * other side's exact wording to this target's negatives.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");

const ROUTING = path.join(os.homedir(), ".claude", "hooks", "routing");

let tokenize, buildIndex, scoreDoc, findScenariosFiles;
try {
  ({ tokenize } = require(path.join(ROUTING, "tokenize")));
  ({ buildIndex, scoreDoc } = require(path.join(ROUTING, "bm25")));
  ({ findScenariosFiles } = require(path.join(ROUTING, "paths")));
} catch (err) {
  console.error(
    `Routing hooks not found under ${ROUTING}.\n` +
      "This script only reports on an existing global router; it does not install one.",
  );
  process.exit(2);
}

const MIN_POS = 8;
const MIN_NEG = 2;

function loadScenarios() {
  const out = [];
  for (const file of findScenariosFiles()) {
    let data;
    try {
      data = JSON.parse(fs.readFileSync(file, "utf8"));
    } catch {
      console.error(`skipped unreadable ${file}`);
      continue;
    }
    if (!data || typeof data.target !== "string" || !Array.isArray(data.positive)) {
      continue;
    }
    const scope = file.includes(path.join(".claude", "routing-corpus"))
      ? "project"
      : "global";
    for (const p of data.positive) {
      out.push({ target: data.target, prompt: p, polarity: "pos", scope, tokens: tokenize(p).tokens });
    }
    for (const n of data.negative || []) {
      out.push({ target: data.target, prompt: n, polarity: "neg", scope, tokens: tokenize(n).tokens });
    }
  }
  return out;
}

function bestAgainst(query, docs, idf, avgdl) {
  let best = 0;
  for (const doc of docs) {
    if (doc === query) continue;
    const s = scoreDoc(query.tokens, doc, idf, avgdl);
    if (s > best) best = s;
  }
  return best;
}

/** Mirrors calibrateThresholds in build-index.js: maximise F-beta with beta^2 = 4. */
function calibrate(posScores, negScores) {
  const candidates = [...new Set([...posScores, ...negScores])]
    .filter((c) => c > 0)
    .sort((a, b) => a - b);
  if (!candidates.length) return null;

  let best = null;
  for (let i = 0; i < candidates.length; i++) {
    const tau = i === 0 ? candidates[0] - 0.001 : (candidates[i - 1] + candidates[i]) / 2;
    if (tau <= 0) continue;
    const TP = posScores.filter((s) => s >= tau).length;
    const FN = posScores.length - TP;
    const FP = negScores.filter((s) => s >= tau).length;
    const precision = TP + FP === 0 ? 0 : TP / (TP + FP);
    const recall = TP + FN === 0 ? 0 : TP / (TP + FN);
    const f1 = precision + recall === 0 ? 0 : (2 * precision * recall) / (precision + recall);
    const fbeta2 =
      4 * precision + recall === 0 ? 0 : (5 * precision * recall) / (4 * precision + recall);
    if (!best || fbeta2 > best.fbeta2) {
      best = { tau, TP, FP, FN, precision, recall, f1, fbeta2 };
    }
  }
  return best;
}

function analyse(scenarios) {
  const index = buildIndex(scenarios);
  const targets = [...new Set(scenarios.map((s) => s.target))].sort();
  const rows = [];

  for (const target of targets) {
    const positives = scenarios.filter((s) => s.target === target && s.polarity === "pos");
    const negatives = scenarios.filter((s) => s.target === target && s.polarity === "neg");
    const foreign = scenarios.filter((s) => s.polarity === "pos" && s.target !== target);
    const scope = positives[0]?.scope ?? "global";

    if (positives.length < MIN_POS || negatives.length < MIN_NEG) {
      rows.push({
        target,
        scope,
        status: "excluded",
        note: `needs >= ${MIN_POS} positives (has ${positives.length}) and >= ${MIN_NEG} negatives (has ${negatives.length})`,
      });
      continue;
    }

    const posScores = positives.map((p) => bestAgainst(p, positives, index.idf, index.avgdl));
    const negEntries = [...negatives, ...foreign].map((n) => ({
      entry: n,
      score: bestAgainst(n, positives, index.idf, index.avgdl),
    }));
    const metrics = calibrate(posScores, negEntries.map((n) => n.score));

    if (!metrics) {
      rows.push({ target, scope, status: "conflict", note: "no separating threshold" });
      continue;
    }

    rows.push({
      target,
      scope,
      status: metrics.f1 >= 0.6 ? "ok" : "conflict",
      ...metrics,
      collisions: negEntries
        .filter((n) => n.score >= metrics.tau)
        .sort((a, b) => b.score - a.score)
        .map((n) => ({ score: n.score, from: n.entry.target, prompt: n.entry.prompt })),
    });
  }

  return rows;
}

function main() {
  const only = process.argv[2];
  const scenarios = loadScenarios();
  if (!scenarios.length) {
    console.error("No scenarios found. Is CLAUDE_PROJECT_DIR set?");
    process.exit(1);
  }
  const rows = analyse(scenarios);

  const projectCount = scenarios.filter((s) => s.scope === "project").length;
  console.log(
    `${scenarios.length} scenarios across ${rows.length} targets ` +
      `(${projectCount} from this project)\n`,
  );

  const pad = (s, n) => String(s).padEnd(n);
  console.log(pad("target", 26) + pad("scope", 9) + pad("status", 10) + pad("f1", 7) + pad("prec", 7) + pad("rec", 7) + "FP");
  console.log("-".repeat(72));
  for (const r of rows) {
    if (r.status === "excluded") {
      console.log(pad(r.target, 26) + pad(r.scope, 9) + pad("excluded", 10) + r.note);
      continue;
    }
    console.log(
      pad(r.target, 26) +
        pad(r.scope, 9) +
        pad(r.status, 10) +
        pad(r.f1.toFixed(2), 7) +
        pad(r.precision.toFixed(2), 7) +
        pad(r.recall.toFixed(2), 7) +
        r.FP,
    );
  }

  const conflicts = rows.filter((r) => r.status === "conflict");
  const shown = only ? rows.filter((r) => r.target === only) : conflicts;

  for (const r of shown) {
    if (!r.collisions?.length) continue;
    console.log(`\n${r.target}: ${r.collisions.length} prompt(s) cross tau=${r.tau.toFixed(2)}`);
    for (const c of r.collisions.slice(0, 10)) {
      console.log(`   ${c.score.toFixed(2)}  [${c.from}]  ${c.prompt}`);
    }
  }

  if (conflicts.length && !only) {
    console.log(`\n${conflicts.length} target(s) in conflict. Rephrase, or add the colliding wording to negatives.`);
  }
  process.exit(conflicts.length ? 1 : 0);
}

main();
