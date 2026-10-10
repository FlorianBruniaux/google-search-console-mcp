# Bounded native audit, source prototype

This optional source workflow acquires an explicit read-only request plan once, then gives immutable observations to a native report author and a separate reviewer invocation. It does not implement the former JavaScript Workflow host or every specialist role. Expert report quality remains gated by human cases in #6.

The source changes are unreleased. Use a checkout containing them and its Python environment; installing the published 1.5.0 wheel alone does not supply this workflow. Default MCP discovery remains unchanged at 96 tools. The query prototypes add no MCP tool.

## Prepare an explicit run

Create a private existing directory for the caller-owned ledger and reports. The configuration is not a credential file and is never installed globally.

```json
{
  "run_id": "my-reviewed-audit",
  "site": "sc-domain:example.com",
  "bing_site": "https://example.com/",
  "ledger_path": "/absolute/private-directory/run.sqlite",
  "max_provider_attempts": 20,
  "max_tool_calls": 20,
  "allowed_tools": ["get_capabilities", "get_search_analytics", "indexing_evidence_matrix"]
}
```

`example.com` and the path are examples to replace with the authorized property and a real absolute private path. Selecting a tool does not grant provider access. GA4 tools additionally require `ga4_property`, for example `"123456789"`; the caller's explicit property overrides ambient GA4 defaults and conflicting arguments are refused.

A request file is a JSON array of `{tool, arguments}` records. For an offline sample:

```json
[
  {
    "tool": "indexing_evidence_matrix",
    "arguments": {
      "site": "sc-domain:example.com",
      "urls": ["https://example.com/page"]
    }
  }
]
```

```sh
python scripts/run_bounded_audit.py --config /absolute/config.json \
  --requests /absolute/requests.json --output /absolute/new-report.json
```

This command acquires the declared plan, without a model invocation by default. Every request is scope-checked before the first acquisition. Writes and unlisted tools are refused. Provider exceptions remain unavailable beside unrelated results. Output is created privately and an existing output is never overwritten.

## Optional native author and reviewer

Add `--host codex --model gpt-6.1-sol` to the command. That host/model combination completed the synthetic offline source run on 10 October 2026. The adapter uses high reasoning, ephemeral sessions, an empty temporary working directory, ignored Codex user configuration, read-only sandbox and disabled web search. It instructs the model to use the packet only; the Codex sandbox still permits read-only commands. This is not a general denial of every possible tool invocation.

`--host claude --model <caller-supported-Claude-model>` uses high effort, no built-in tools and an empty strict MCP configuration. The installed Claude CLI completed the same offline-source draft/reviewer path on 10 October 2026 using its supported `opus` alias and high effort. This observes that packet path, not diagnostic accuracy, authenticated SEO acquisition or specialist dispatch. Supply a model supported by that native host, not a Codex alias; the `opus` alias can resolve differently after a host update.

There are at most two native invocations: author, then a fresh reviewer with sources and draft. Host errors retain acquired observations and mark native execution unavailable. Supported facts require a pointer into acquired observations; a draft reference alone cannot establish support. The structural validator checks claim shape and source boundaries, not whether a claim is semantically supported. Human labels are not provided to either model. Native model calls are separate from provider-attempt accounting; no measured cost or diagnostic accuracy is claimed.

Input and returned reports are byte-limited, but native process log/output files are only inspected after execution. This prototype does not enforce a disk-write ceiling while the child runs; its timeout bounds process duration. No resource-exhaustion case was reproduced during review.

## Budget and cache contract

The caller-owned SQLite ledger atomically reserves attempts under one run ID across sessions/processes. A changed configuration for that ID is rejected. It does not reset at process restart. Reusing an ID continues its budget; choose a new explicit ID for a new run. Delete a ledger only as an explicit caller cleanup action when its run records are no longer needed.

Google HTTP dispatch is counted at the connection's request boundary, including httplib2 internal retries and credential-replay attempts within that transport. Connection setup before HTTP dispatch, standalone credential resolution, other network clients and ancillary HTML/CrUX fetches are outside this contract. Bing retries reserve before each HTTP attempt. Budgeted GA4 clients disable GAPIC and gRPC transparent retries; each RPC dispatch reserves an attempt. Failed dispatches are retained. The allowlist excludes tools that require unaccounted ancillary fetches. Transport fixtures are not fresh provider measurements.

Acquisition in one session is serialized. Concurrent identical requests receive one immutable JSON response; decoded edits cannot mutate the cached string. The cache is session-local, bounded to 8 MB total and 2 MB per observation, and is not persisted. A different process can reacquire data, but uses the same durable attempt ceiling. Tool calls, including cache hits, have a separate bound. The ledger records reservation counts, not detailed timing or a provider-success claim.

To expose only the selected audit tools through a dedicated MCP server process, set `GSC_MCP_AUDIT_CONFIG=/absolute/config.json` in that process's environment before starting it. This changes that process's startup surface only. No client settings or global skill files are changed by this repository. Discovery returns the actual reduced list and the run budget scope.

## Human report evaluation

`scripts/eval_audit_reports.py` handles three claim-review tracks: traffic diagnosis, harmful competition and report fidelity. It is separate from query classification and does not measure extraction inclusion/omission or page-pair similarity.

Each corpus declares `schema_version: 1`, `corpus_id`, `provenance` (`human` or `synthetic`) and `cases`. Each case supplies an ID, family ID, split, track, FR/EN language, source observations, reviewed claims and annotation provenance. An annotation names distinct annotator/reviewer identities, source authorization and disagreement resolution. Labels are `supported`, `unsupported` or `unresolved`, each with source references that resolve inside the case observations. Related families cannot cross train/tuning/held-out splits.

```sh
python scripts/eval_audit_reports.py --dataset /absolute/reviewed-corpus.json --prepare
python scripts/eval_audit_reports.py --dataset /absolute/reviewed-corpus.json \
  --predictions /absolute/independent-claim-predictions.json
```

Preparation emits only selected observations and case/task identifiers, without expected claims or human labels. Prediction input supplies the corpus ID, split, independent reviewer identity and records with `case_id`, `claim_id`, `label`. Missing predictions count in the full denominator; per-track counts expose unsupported-as-supported errors. These are caller-declared identities, not verified human identities. The release gate remains unavailable until task targets and a human approval decision are supplied outside this scaffold.

## Offline query prototypes

`scripts/query_rules_baseline.py` produces intent predictions compatible with the existing offline evaluator. It reads query text/language and caller brand terms, not gold labels. The rule prototype separates question form from intent and abstains on mixed or negative lexical signals. `query_rules.near_query_candidates` retains variants and order and marks equal intent unknown. It does not sort tokens, remove negation or silently merge routes such as Paris/Londres and Londres/Paris.

```sh
python scripts/query_rules_baseline.py --dataset /absolute/query-corpus.json \
  --split held_out --brand-terms '["caller-brand"]' > /absolute/predictions.json
python scripts/eval_classifier.py --dataset /absolute/query-corpus.json \
  --predictions /absolute/predictions.json
```

Both prototypes stay outside the public registry. Synthetic fixture output is ineligible for release and is not a benchmark for real FR/EN queries. #4/#5 still require human-approved taxonomy, thresholds and held-out results. No embeddings or paid classifier backend is added.
