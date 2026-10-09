"""Execute the workflow with a controlled Node host, never a live agent/provider.

These checks catch unknown-to-false routing, dropped optional failures, bypassed
scheduling bounds, and review inputs that omit the source observations or draft.
They do not validate model behavior or native Claude/Codex runtime availability.
"""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="controlled host needs Node")

HOST = r'''
const fs = require('fs');
const config = JSON.parse(process.argv[1]);
const source = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta');
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
const calls = [];
let active = 0, peak = 0;
const sourceObservation = {tool:'inspect_url', url:'https://example.com/p0', _meta:{evidence:{status:'unavailable', observed_window:null}}, verdict:'UNKNOWN'};
function validate(value, schema) {
  if (!schema) return;
  for (const key of schema.required || []) {
    if (!(key in value)) throw new Error('schema missing ' + key);
  }
  for (const [key, definition] of Object.entries(schema.properties || {})) {
    if (!(key in value) || !definition.type) continue;
    const kinds = [].concat(definition.type);
    const kind = value[key] === null ? 'null' : Array.isArray(value[key]) ? 'array' : typeof value[key];
    if (!kinds.includes(kind)) throw new Error('schema rejects ' + key + ':' + kind);
  }
}
async function agent(prompt, options) {
  calls.push({prompt, options}); active++; peak = Math.max(peak, active);
  try {
    await new Promise(resolve => setTimeout(resolve, 2));
    if (config.failLabel === options.label) throw new Error('optional provider unavailable');
    if (config.nullLabel === options.label) return null;
    let value;
    if (options.label === 'discovery') value = {siteUrl:'sc-domain:example.com', isAccessible: config.accessible === undefined ? true : config.accessible, topUrls:Array.from({length:20}, (_,i)=>'https://example.com/p'+i), observations:[sourceObservation]};
    else if (/^page-\d+$/.test(options.label)) value = {url:'https://example.com/p'+(Number(options.label.slice(5))-1), healthScore:config.score ?? null, isIndexed:config.indexed ?? null, observations:[sourceObservation], topQueries:[]};
    else if (options.label === 'synthesis') value = 'DRAFT: indexing UNKNOWN; AI exposure unavailable';
    else if (options.label === 'evidence-review') value = {status:'reviewed', findings:[{type:'unsupported_claim', claim:'impact', source_refs:['/pageAnalysis/0/observations/0'], correction:'unavailable'}]};
    else value = {status:'observed', observations:[sourceObservation]};
    validate(value, options.schema);
    return value;
  } finally { active--; }
}
const parallel = jobs => Promise.all(jobs.map(job => job()));
const pipeline = (items, first, second) => Promise.all(items.map(async (item, i) => second(await first(item, null, i), item, i)));
(async () => {
  try {
    const fn = new AsyncFunction('args','agent','parallel','pipeline','phase','log', source);
    const result = config.noHost ? await fn(config.args) : await fn(config.args, agent, parallel, pipeline, ()=>{}, ()=>{});
    console.log(JSON.stringify({result,calls,peak}));
  } catch (error) { console.log(JSON.stringify({error:error.message,calls,peak})); }
})();
'''


def run_workflow(**config):
    config.setdefault("args", {"siteUrl": "sc-domain:example.com", "maxPages": 2, "maxConcurrentAgents": 2})
    result = subprocess.run([NODE, "-e", HOST, json.dumps(config), str(ROOT / ".claude/workflows/mega-audit.js")], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def observations_from(data, label):
    prompt = next(call["prompt"] for call in data["calls"] if call["options"]["label"] == label)
    return json.loads(prompt.split("SOURCE_OBSERVATIONS:\n", 1)[1].split("\nEND_SOURCE_OBSERVATIONS", 1)[0])


def test_missing_host_fails_clearly_before_side_effects():
    data = run_workflow(noHost=True)
    assert "Unsupported workflow runtime" in data["error"]
    assert data["calls"] == []


def test_unknown_nullable_page_data_reaches_review_without_deepdive():
    data = run_workflow()
    assert "error" not in data, data
    labels = [call["options"]["label"] for call in data["calls"]]
    assert not any(label.startswith("page-deepdive-") for label in labels)
    source = observations_from(data, "evidence-review")
    assert source["pageAnalysis"][0]["isIndexed"] is None
    assert source["pageAnalysis"][0]["healthScore"] is None
    assert source["pageAnalysis"][0]["observations"][0]["_meta"]["evidence"]["status"] == "unavailable"
    prompt = next(call["prompt"] for call in data["calls"] if call["options"]["label"] == "evidence-review")
    assert "DRAFT: indexing UNKNOWN; AI exposure unavailable" in prompt
    assert '"unsupported_claim"' in data["result"]


@pytest.mark.parametrize("score,indexed,deepdive", [(80, True, False), (20, None, True), (None, False, True), (None, None, False)])
def test_deepdive_requires_observed_failure(score, indexed, deepdive):
    data = run_workflow(score=score, indexed=indexed)
    assert "error" not in data, data
    labels = [call["options"]["label"] for call in data["calls"]]
    assert ("page-deepdive-1" in labels) is deepdive


def test_page_count_and_concurrent_agent_calls_are_bounded():
    data = run_workflow()
    assert "error" not in data, data
    pages = [call for call in data["calls"] if call["options"]["label"].removeprefix("page-").isdigit()]
    assert len(pages) == 2
    assert data["peak"] <= 2


def test_optional_provider_failure_is_preserved_for_review():
    data = run_workflow(failLabel="external-research")
    assert "error" not in data, data
    source = observations_from(data, "evidence-review")
    assert source["securityResearch"][1] == {"status": "unavailable", "agent": "external-research", "error": "optional provider unavailable"}


def test_review_failure_marks_draft_unreviewed():
    data = run_workflow(failLabel="evidence-review")
    assert "error" not in data, data
    assert "unreviewed" in data["result"]
    assert "optional provider unavailable" in data["result"]


def test_missing_optional_agent_result_is_not_dropped_from_sources():
    data = run_workflow(nullLabel="page-1")
    assert "error" not in data, data
    source = observations_from(data, "evidence-review")
    assert source["pageAnalysis"][0] == {"status": "unavailable", "agent": "page-1", "error": "agent returned no result"}
    assert len(source["pageAnalysis"]) == 2


@pytest.mark.parametrize("arguments", [{"siteUrl":"sc-domain:example.com", "maxPages":0}, {"siteUrl":"sc-domain:example.com", "maxConcurrentAgents":0}])
def test_invalid_bounds_fail_before_agent_calls(arguments):
    data = run_workflow(args=arguments)
    assert "error" in data
    assert data["calls"] == []
