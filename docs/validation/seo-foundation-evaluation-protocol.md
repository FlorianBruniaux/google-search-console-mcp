# SEO foundation evaluation protocol and missing human inputs

Issue #6, C1. Source baseline: `4ac51aa53e5608d175ead22f0afb4855c9e4a491`. This protocol provides an intake contract, not human labels or a quality approval.

C1 supports query intent/pairs, claim fidelity/traffic/harmful-competition tracks and the existing extraction snippet comparison. It does not certify all 96 MCP tools, native-host behavior, causality or semantic rewrite fidelity.

## Technical interfaces

| Task | Inputs and runner | Measures and boundary |
|---|---|---|
| Query intent | Query corpus + independent predictions + optional query manifest; `scripts/eval_classifier.py` | Class support/precision/recall, full-set accuracy, coverage and abstention; FR/EN breakdown. Legacy undefined class metrics use zero fill; review support before interpreting them. |
| Query pairs | Same runner, separate `task: pairs` corpus records/predictions/targets | Same/distinct/unclassified outcome judgments. Cross-language pairs are grouped under `mixed`, not one member's language. |
| Report claims | Corpus + predictions + optional report manifest; `scripts/eval_audit_reports.py` | Confusion, support, precision/recall, missing predictions and false-supported counts by track/language/label. No prose completeness or causal truth assessment. |
| Extraction | Annotated local HTML manifest; `scripts/eval_content_extraction.py` | Snippet inclusion/omission and per-case profile comparisons. Not whole-content precision/recall, downstream warning evaluation or RSS. |

Query and report JSON files are bounded to 2,000,000 bytes each. Report corpora contain 1 to 500 cases, at most 100 claims per case. Extraction keeps its existing 100-case/HTML/corpus byte limits. Independent batches may be evaluated separately; do not average them into a release decision without a declared weighting/aggregation protocol.

## Human inputs still missing for C1

No authenticated human batch or approval evidence has been supplied for this work. Controlled test records, including tests that declare `human`, are authored synthetic mechanics checks. Private data outside the supplied checkout were not searched.

| ID | Required material | Exact content and completion check |
|---|---|---|
| H1 | Authorized source register | Owner, permitted use/sharing/retention, anonymization record, private approval evidence and non-identifying reference. Exact input bytes and SHA-256; no secrets in Git. |
| H2 | FR/EN intent corpus | Real queries with ID, language, family, split and one of five `query-intent-v1` labels. Include brand, questions seeking action, negation, mixed intent, directional terms and unresolved cases. Initial collection aim is about 200 queries, not a universal adequate sample. |
| H3 | Independent query-pair corpus | Pair IDs and both existing query IDs, same/distinct/unclassified outcome labels, family/split and reviewer judgments. Include broad-intent agreement with different outcomes, reversals, translations and ambiguous relations. Query labels alone cannot label pairs. |
| H4 | Three claim-review batches | FR/EN packets for `report_fidelity`, `traffic_diagnosis`, `harmful_competition`: effective property/provider, tool/request versions, observed/requested windows, timezone, coverage, errors and original observations. Real candidate reports, human-extracted claim IDs/text, source pointers and supported/unsupported/unresolved judgments are required. |
| H5 | Independent extraction annotations | Authorized UTF-8 HTML + raw source URL/acquisition context and SHA-256 for article, product, local service, forum and JS-shell families in FR/EN. Human inclusion snippets and omission snippets with template/comment/other kind, source location review and extractor-independent judgments. Do not use candidate output as gold text. |
| H6 | Actual annotation/review evidence | Distinct human annotator/reviewer participation, original labels, disagreements and adjudication reasons. Identity/consent strings in JSON and casefold checks are declarations, not authentication. The report prediction reviewer also differs from label authors. |
| H7 | Reviewed family/split and access record | Related sites/events/pages/revisions, paraphrases/translations and variants remain in one partition. Record who accessed held-out labels; supply label-free author packets separately. The validators detect declared overlap only. |
| H8 | Pre-tuning numerical target approval | Required support by task/label/language/genre, allowed false-supported claims, precision/recall, coverage/abstention and failure rules. Exact dataset/label/split/target bytes/hashes plus external chronology/review reference. Values are currently missing, not supplied by demonstration fixtures. |
| H9 | Independent actual run artifacts | Input packet IDs/hashes, candidate/baseline versions and predictions. Same frozen evaluation split for comparisons; retain errors and omissions. If a model is compared, separately retain actual cost, latency and complete probability vectors where measured. A paid model is not required for C1. |
| H10 | Per-task human release decision | Reviewer decision bound to corpus, manifest and prediction hashes, observed support/errors, unassessed strata and justified exceptions. Publish only approved anonymized results. Met numerical targets alone do not supply this decision. |

For H4, human reviewers also need a case-level sidecar recording source preservation, contradictions, evidence omitted from the candidate report, proposed action and its conditionality. Existing claim labels score supplied claims, not unmentioned facts. Preserve genre/type metadata in that sidecar; corpus v1 has no genre field.

### Required claim case coverage

- **Report fidelity:** multi-property packets, wrong source/window attribution, partial collection, measured zero versus unavailable, unknown indexing, contradictory rows and bounded report omissions.
- **Traffic diagnosis:** reporting lag, missing rows, historical spike, seasonal/weekday references, collection incident, property/timezone mismatch and low support. Label what the packet supports, not an invented true cause.
- **Harmful competition:** category/product coexistence, distinct intent/market, brand navigation, migration and material URL alternation. Shared queries, similarity or a SERP rank alone cannot authorize consolidation.
- Each track needs both FR and EN, all supported labels at the pre-agreed support, and independently reviewed family isolation. Counts/minimums must be approved before tuning, not selected after results.

## Freeze and run

1. Complete H1/H6 authorization and participation records in a private approved location.
2. Collect H2/H3/H4/H5 as separate task corpora. Review families and stratification H7.
3. Resolve disagreements and freeze input/labels/splits/H8 targets. Preserve chronological evidence outside JSON declarations.
4. Produce label-free author inputs and retain access records. Extract/map candidate report claims with an independent review before scoring.
5. Run existing baselines and candidates against identical task-specific held-out sets. Record language and support failures, not only averages.
6. Review H10 per task. No successful CLI exit or synthetic threshold pass closes #6.

Report `--manifest` requires `--predictions` and held-out targets. It is refused with `--prepare`. Its reference schema is the explicitly synthetic `tests/fixtures/audit_evaluation/report_targets.synthetic.json`, whose hash binds real fixture bytes. Numbers in that file are boundary checks, not suggested production goals.

Report `target_assessment` is `unavailable`, `insufficient_support`, `failed` or `met`. Every target is a track/language/label tuple. Precision/recall refer to that label, coverage and false-supported ceiling to the entire track/language stratum. `untargeted_strata` lists observed nonzero-support labels outside the supplied targets; a missing manifest leaves all observed strata untargeted. These results cover listed targets only. Report `release_gate` stays `unavailable`.

Query targets retain the existing schema and overall task checks, not new per-language automatic approval. Use the language breakdown and external H8/H10 review for language-specific decisions. Extraction criteria remain in its separate protocol and human C3 review; C1 adds no extraction adoption gate.

## Additional issue #6 tasks outside this C1 interface

Editorial/rewrite quality needs authorized passages and original/revision judgments with task-specific adapters. Page similarity needs independent page-pair judgments, not query pairs. Instruction detection/readiness, controlled follow-up and research retrieval require their own positive/benign, causal-protocol or passage-relevance corpora and adapters. These remain unassessed even if the supported C1 tasks pass.

Skills used: flow-lean, superpowers:executing-plans, superpowers:test-driven-development, superpowers:verification-before-completion

