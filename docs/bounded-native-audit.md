# Bounded native audit, source prototype

This optional source workflow acquires an explicit read-only request plan once, then gives immutable observations to selected source-only specialists, a report author and a separate reviewer invocation. Both native CLI hosts use the same packaged role contracts. It does not implement the former JavaScript Workflow host, interactive skill routing or ancillary HTML/CrUX acquisition. Expert report quality remains gated by human cases in #6.

Version 1.6.0 packages the experimental acquisition and native audit APIs, including nine source-review profiles. Use a repository checkout and its Python environment for the runner scripts and workspace skills; the wheel does not install these as console commands. Default MCP discovery remains unchanged at 96 tools. The query prototypes add no MCP tool.

The [recorded offline runs](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/2026-10-10-native-specialists.md) on 10 October 2026 each used 4 native attempts, 2 local tool calls and 0 provider attempts, under separate run IDs for Codex and Claude. These historical observations do not describe a current authenticated provider run. The [later controlled resource checks](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/2026-10-10-delegated-evaluation-native-limits.md) test harmless local children and the offline extraction runner separately.

## Source checkout and prerequisites

The separate [authenticated GSC pilot](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/2026-10-10-live-gsc-readiness.md) records real Google acquisition and native reviews of identical private projections, including partial coverage and a provider-budget limit. The [C1 follow-up](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/2026-10-11-claude-c1-followup.md) records eight controlled interactive-playbook cases passing only their frozen missing-count criteria. It uses MCP replay without new provider acquisition. These are distinct validation paths; neither approves whole-report accuracy or human SEO quality, and #39 remains open.

Use Python 3.11 or later from the repository root. On Linux or macOS, prepare a source environment:

```sh
git clone https://github.com/FlorianBruniaux/google-search-console-mcp.git
cd google-search-console-mcp
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Native invocations additionally require an installed, authenticated Codex or Claude CLI and a model supported by that host. Native mode supports Linux and macOS. Acquisition-only mode skips native subprocesses; follow the core package’s [installation requirements](installation.md). These setup commands do not grant provider access or authorize model calls. Human report quality and authenticated provider acquisition remain unverified by the offline host runs described below.

For independent quality targets, use the [human evaluation intake](expert-evaluation-intake.md). The [query evaluator](classifier-evaluation.md) and [local extraction comparison](content-extraction.md#offline-annotated-comparison) use separate annotations and do not certify native report quality.

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
  "max_native_calls": 6,
  "allowed_tools": ["get_capabilities", "get_search_analytics", "indexing_evidence_matrix"]
}
```

`example.com` and the path are examples to replace with the authorized property and a real absolute private path. Google-only configurations may omit `bing_site`; authorizing a Bing tool or `compare_search_engines` requires its explicit valid URL. Removing that field from a recorded configuration changes its identity and requires a new run ID. Selecting a tool does not grant provider access. GA4 tools additionally require `ga4_property`, for example `"123456789"`; the caller's explicit property overrides ambient GA4 defaults and conflicting arguments are refused.

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

This command acquires the declared plan, without a model invocation by default. Every request is scope-checked before the first acquisition. The CLI forces `GSC_NO_BROWSER=1`; prepare missing authentication separately. It rejects an existing or symbolic-link output and a missing parent directory before acquisition. Writes and unlisted tools are refused. Provider exceptions remain unavailable beside unrelated results. Output is created privately and an existing output is never overwritten.

## Optional native author and reviewer

Add `--host codex --model gpt-6.1-sol` to the command. That host/model combination completed the synthetic offline source run on 10 October 2026. The adapter uses high reasoning, ephemeral sessions, an empty temporary working directory, ignored Codex user configuration, read-only sandbox and disabled web search. It instructs the model to use the packet only; the Codex sandbox still permits read-only commands. This is not a general denial of every possible tool invocation.

`--host claude --model <caller-supported-Claude-model>` uses high effort, no built-in tools and an empty strict MCP configuration. The installed Claude CLI completed the offline-source draft/reviewer path on 10 October 2026 using its supported `opus` alias and high effort. This observes that packet path, not diagnostic accuracy or authenticated SEO acquisition. Supply a model supported by that native host, not a Codex alias; the `opus` alias can resolve differently after a host update.

Without specialists the path attempts an author and then a fresh reviewer. The optional `max_native_calls` configuration bounds native reservations per run, from 1 to 64, default 2. Every invocation reserves before launch, including failures; reopening a run continues that count. This ceiling applies to this orchestrated path, not unrelated CLI sessions. It counts attempts, not tokens, billed cost or duration. Adding the setting to an existing immutable configuration requires a new run ID. Earlier prototype invocations before this counter existed are not reconstructed.

Host errors retain acquired observations and mark the affected branch unavailable. Supported facts require a pointer into acquired observations; a draft or specialist reference alone cannot establish support. The structural validator checks claim shape and source boundaries, not whether a claim is semantically supported. Human labels are not provided to the models. Native model calls are separate from provider-attempt accounting; no measured cost or diagnostic accuracy is claimed.

## Optional source-only specialists

Repeat `--specialist` to choose roles explicitly, and optionally set `--max-native-concurrency 2`. The concurrency bound accepts 1..4, defaults to 1 and applies within this pipeline; synthesis and review remain sequential. Every role uses the explicit caller model and high reasoning/effort. No host-specific model alias is copied into another host's configuration.

```sh
python scripts/run_bounded_audit.py --config /absolute/config.json \
  --requests /absolute/requests.json --output /absolute/new-report.json \
  --host codex --model gpt-6.1-sol \
  --specialist gsc-indexing-auditor --specialist gsc-sitemap-auditor \
  --max-native-concurrency 2
```

The nine projections in `src/gsc_mcp/native_roles.py` correspond to the repository's SEO role names:

| Role | Supplied sources used; retained boundary |
|---|---|
| `gsc-seo-reporter` | Performance, period comparisons, alerts; no invented health score or penalty |
| `gsc-traffic-doctor` | Dated comparisons, traffic candidates and daily references; causes remain hypotheses |
| `gsc-ai-overviews-analyst` | Generic search observations; AI exposure and causal loss remain unavailable without a source |
| `gsc-indexing-auditor` | Selected inspections and evidence matrices; unknown verdicts and sample limits remain explicit |
| `gsc-sitemap-auditor` | Submitted sitemap inventory and separate URL inspections; no submitted/indexed ratio |
| `gsc-schema-auditor` | Supplied schema validation; this acquisition allowlist excludes its ancillary HTML tool, so the current CLI marks it unavailable |
| `gsc-cannibalization-checker` | Query/page overlap and inspections; overlap alone does not justify consolidation |
| `gsc-content-optimizer` | Rule-selected opportunities and retrieved queries; no promised ranking gain |
| `gsc-page-analyst` | Supplied page performance and inspections; missing HTML/schema/rendering/vitals remain unavailable |

These are deliberately narrower source-review contracts than the interactive roles in `.claude/agents/`. They do not load or execute the playbooks or enable the roles' MCP tools. Selection never adds acquisition requests. A specialist receives a fresh decoded copy of the original observations, with matching usable observation indices declared in `role_scope`; reference validation rejects pointers into other observations and whole-collection pointers. References to temporary `role_scope` metadata are rejected for every claim status because this field is absent from the final packet. Original indices remain stable. This is a reference boundary, not semantic proof or a confidentiality filter: the original packet is visible to the selected model.

Missing sources, failed sources, model failures and exhausted budgets have separate unavailable reasons beside successful branches. Specialists leave two currently available slots for synthesis/review. Another process sharing the run can consume those slots; the durable ceiling still refuses dispatch before excess attempts. Restarted processes may acquire again under the provider budget, because observations are cached only within one acquisition session.

The final packet retains `specialists`, `draft`, `review`, explicit native host/model/effort/concurrency, and cumulative counts. `partial; semantic_quality_unverified` means at least one selected branch was unavailable; returned review is not approval of a site change. An unavailable schema branch does not establish valid schema. Two generated reports agreeing does not replace independent human evaluation.

Each retained generated report is limited to 128,000 UTF-8 JSON bytes. With nine distinct roles plus author/reviewer, retained report bodies cannot exceed 1,408,000 bytes in aggregate. Oversized reports become an unavailable branch before aggregation, without trimming source evidence. Synthesis/review input still has the 2 MB packet ceiling; if the original sources plus generated material exceed it, that branch is unavailable and observations remain retained. Malformed claim types or a malformed Claude response envelope likewise fail only their branch.

Native execution on Linux and macOS bounds stdout and stderr separately to 2,000,000 bytes while the child runs. Stdout is retained in bounded memory; stderr is counted and discarded by default. A caller of `run_bounded` can explicitly supply `stderr_path` for an exclusive `0600` diagnostic file. The parent writes only chunks admitted under the same stderr ceiling; the child keeps its bounded pipe. Crossing either stream ceiling stops the invocation and leaves its branch unavailable, with observations and its durable attempt reservation retained. Child output is never copied into failure messages.

A separate Python launcher installs an inherited hard `RLIMIT_FSIZE` ceiling before executing the host. The default remains the output ceiling. The Codex adapter explicitly allows up to 16,000,000 bytes per regular file so a session SQLite/WAL commit larger than 2 MB can complete. Lower inherited soft or hard limits still win. This affects host state outside the temporary directory too; it is not an aggregate disk quota or a memory limit.

The accepted final report remains strictly below 2,000,000 bytes. With the larger Codex state allowance, that output threshold is monitored and checked before reading, rather than enforced as a 2 MB kernel write limit; a file can temporarily grow up to the separate regular-file ceiling and is then rejected. Calls retaining the default allowance keep the smaller kernel ceiling.

Codex success requires a consistent native thread identifier, `turn.started`, `turn.completed` and a final JSON assistant message. A zero process exit, a returned tool result or a report file alone is insufficient. When the last-message file is missing, the completed assistant message can supply the report without another model call. If the file exists, its decoded value must match that message. A captured resumed turn can be checked with `parse_codex_response(..., expected_thread_id=...)`; this does not initiate a resume. Source references and claim shape are validated separately. Stable `failure_reason` codes remain beside unavailable specialist branches and in `native_execution` for synthesis/review; no raw host errors are included. There is no automatic native retry or provider reacquisition.

Each invocation starts a new process group. Completion, timeout and output overflow kill remaining members of that group and reap the direct child before temporary-file cleanup. Descendants that deliberately detach into another group are outside that cleanup guarantee; the operating system reaps orphaned descendants. Concurrent specialists use separate launchers and groups, without changing the parent's resource limits or using a threaded `preexec_fn`. Other platforms are explicitly unavailable for native execution; acquisition-only runs remain available. These boundaries use Python's documented [process sessions and thread-safe launch options](https://docs.python.org/3/library/subprocess.html#subprocess.Popen), [file resource limits](https://docs.python.org/3/library/resource.html#resource.RLIMIT_FSIZE) and [process-group signals](https://docs.python.org/3/library/os.html#os.killpg).

Local harmless Python-child tests cover live stdout/stderr overflow, a final writer that catches its write error, timeout, descendant cleanup, concurrent invocations and both host response envelopes. These fixtures exercise resource handling, not real Claude/Codex provider execution or diagnostic accuracy.

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

Preparation emits only selected observations and case/task identifiers, without expected claims or human labels. Prediction input supplies the corpus ID, split, independent reviewer identity and records with `case_id`, `claim_id`, `label`. Missing predictions count in the full denominator; per-track counts expose unsupported-as-supported errors. These are caller-declared identities, not verified human identities. The runner now accepts optional frozen held-out claim targets via `--manifest`; it reports matrices and per-label measures by track/language, with explicit missing predictions and untargeted strata. `release_gate` stays `unavailable` even when numerical targets are met. See the [human intake](expert-evaluation-intake.md#report-targets-and-c1-collection-requirements) for the manifest schema and remaining real-human records.

## Offline query prototypes

`scripts/query_rules_baseline.py` produces intent predictions compatible with the existing offline evaluator. It reads query text/language and caller brand terms, not gold labels. The rule prototype separates question form from intent and abstains on mixed or negative lexical signals. `query_rules.near_query_candidates` retains variants and order and marks equal intent unknown. It does not sort tokens, remove negation or silently merge routes such as Paris/Londres and Londres/Paris.

```sh
python scripts/query_rules_baseline.py --dataset /absolute/query-corpus.json \
  --split held_out --brand-terms '["caller-brand"]' > /absolute/predictions.json
python scripts/eval_classifier.py --dataset /absolute/query-corpus.json \
  --predictions /absolute/predictions.json
```

Both prototypes stay outside the public registry. Synthetic fixture output is ineligible for release and is not a benchmark for real FR/EN queries. #4/#5 still require human-approved taxonomy, thresholds and held-out results. No embeddings or paid classifier backend is added.
