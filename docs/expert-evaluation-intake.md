# Human evaluation intake for issue #6

This contributor worksheet and its linked evaluators require repository resources. The scripts require a [source checkout](bounded-native-audit.md#source-checkout-and-prerequisites); the 1.6.0 wheel does not install them as console commands. The default public catalogue remains 96 tools. The [native audit guide](bounded-native-audit.md) covers execution and its resource boundaries separately from human quality review.

The next input is an authorized, independently reviewed human batch with frozen task-specific targets. This worksheet assigns that work without supplying labels, thresholds or approvals. The existing evaluators run offline; another harness or a paid model backend is not required to start collection.

## Choose the task and matching interface

Keep each task's report and support counts separate. A successful evaluation on one row below cannot approve another task.

| Task | Existing interface | Supported evaluation and remaining boundary |
| --- | --- | --- |
| Query intent, #5 | `scripts/eval_classifier.py`, `task: "intent"` | FR/EN queries under `query-intent-v1`; precision/recall/support per class, accuracy, coverage and abstention. Supplied manifest targets can be checked on `held_out`; human release review remains pending. |
| Query pairs, #4 | Same CLI, `task: "pairs"` | Separate `same_intent`, `distinct_intent` and `unclassified` labels. Both members must exist in the query corpus and occupy the pair's split. Broad intent agreement alone does not label a pair. |
| Report fidelity/native behavior, #39 | `scripts/eval_audit_reports.py`, `track: "report_fidelity"` | Claim labels against observations; optional frozen numerical claim targets. Native-host execution, omitted evidence, free-text parsing and release approval remain outside this interface. |
| Traffic diagnosis | Same CLI, `track: "traffic_diagnosis"` | Claim support from the observed packet, including unknown versus zero and conditional interpretations. The evaluator does not establish the underlying cause or score diagnosis completeness. |
| Harmful competition, #45 | Same CLI, `track: "harmful_competition"` | Claim support for supplied review/consolidation proposals. It does not derive page intent, establish harm or authorize merging pages. |
| Main-content extraction, #41 | `scripts/eval_content_extraction.py`; see [extraction comparison](content-extraction.md#offline-annotated-comparison) | UNSUPPORTED by both CLIs above. The separate runner compares independently annotated inclusion/omission snippets in SHA-bound local HTML; these measures do not estimate whole-content recall or precision. Real human annotations, frozen targets and downstream warning review remain required. |
| Editorial warnings and rewrite fidelity | Task-specific adapter required | UNSUPPORTED by both CLIs. Collect per-rule/genre actionable warnings and original/revision judgments; literal checks remain separate from semantic judgments. |
| Page similarity, #22 | Task-specific adapter required | UNSUPPORTED by both CLIs. Collect page-pair labels with shared templates, translations and legitimate local similarities. Query-pair labels cannot replace these judgments. |
| Instruction detection and readiness, #9 | Task-specific adapter required | UNSUPPORTED by both CLIs. Collect separate positive/benign page tasks and their labels; no citation-probability claim follows from a query score. |
| Controlled follow-up, #47 | Task-specific protocol and adapter required | UNSUPPORTED by both CLIs. Review the estimand/protocol, simulations, pretrend/contamination failures and inconclusive observational cases. |
| Research retrieval, #50 | Task-specific adapter required | UNSUPPORTED by both CLIs. Review consulted passages, relevance, abstract/full-text scope, commercial interest and source-supported wording. |

The report evaluator accepts only `supported`, `unsupported` and `unresolved`. An unresolved claim is a semantic label, not a missing prediction. Its output includes confusion matrices, per-label precision/recall/support, accuracy, missing-prediction coverage and `unsupported_as_supported` counts/rates by track, language and their intersection. Undefined precision/recall/rates are `null` with explicit denominator reasons. Genre-level review and prose completeness remain outside corpus v1. Its `release_gate` is always `unavailable`.

## Report targets and C1 collection requirements

Use `--manifest` with `--predictions` for held-out report targets; it is refused with `--prepare`. Query and report JSON input files are bounded to 2,000,000 bytes each. The query report now includes `by_language` and `manifest_sha256`; bilingual pairs are grouped under `mixed`.

The report manifest requires exactly `schema_version: 1`, `corpus_id`, `dataset_sha256`, `split: held_out`, `annotation_provenance`, a nonempty `review_reference`, `frozen_before_tuning: true` and `targets`. It binds the exact dataset bytes and declared provenance. It does not authenticate its approval reference or chronology.

Each of the 1 to 18 distinct target records requires `track`, `language`, `label`, `min_support` (integer 1 to 50,000), `min_precision`, `min_recall`, `min_coverage` (finite numbers 0 to 1), and `max_unsupported_as_supported` (integer 0 to 50,000). Precision/recall concern the named label; coverage and the false-supported count concern its entire track/language stratum. These are required schema fields, not approved business values.

`target_assessment` is `unavailable` without a manifest, `insufficient_support` if any target lacks its required truth-label support, `failed` when supported targets fail a criterion, or `met` for the listed targets. `target_checks` retains observed values and individual checks. `untargeted_strata` lists observed nonzero-support label strata without targets, including all observed strata when a manifest is absent. A met target does not approve other strata, tasks or release. Dataset, prediction and manifest SHA-256 values identify the evaluated bytes.

A complete runnable synthetic example:

```sh
python3 scripts/eval_audit_reports.py \
  --dataset tests/fixtures/audit_evaluation/report_corpus.synthetic.json \
  --predictions tests/fixtures/audit_evaluation/report_predictions.synthetic.json \
  --manifest tests/fixtures/audit_evaluation/report_targets.synthetic.json
```

Its numeric targets test mechanics only. `synthetic_release_eligible` remains false and `declarations_authenticated` remains false, including controlled fixtures that declare human provenance.

For C1, collect six separate task inputs: real FR/EN intent queries, independently labeled query pairs, the three report-claim tracks, and extraction HTML/snippets. Each needs authorization, real annotation/review participation, original disagreements, reviewed family/split assignment, pre-tuning numerical targets, label-access records and actual independent prediction/review artifacts. Retain genre and omitted-fact/action review as a sidecar keyed by case ID. The report runner cannot identify prose omissions automatically. See the repository-only `docs/validation/seo-foundation-evaluation-protocol.md` for the H1 to H10 delivery checklist; no authenticated batch or approved thresholds have been supplied for this C1 run.

## Complete one batch worksheet

Copy this section for each task. Blank responses mean the evidence or decision is still missing. These worksheet fields are human intake metadata, not a new evaluator JSON schema. Keep private approvals, original observations and identifying content in the approved private location; commit only authorized anonymized records and non-identifying references.

| Intake question | Human response |
| --- | --- |
| Which task, corpus ID, languages and case genres does this batch cover? | |
| Who owns the source data, and what evidence authorizes this exact use and sharing scope? | |
| Where are the anonymized input bytes, their SHA-256 and the private authorization reference? | |
| Who supplies the independent labels, who reviews them, and where is evidence of their real participation retained? | |
| Where are the original labels, disagreements, final decisions and reasons retained? | |
| Which taxonomy/rules were approved, by whom, and at which review reference? | |
| Where is the reviewed family map and split assignment, including related sites/events/queries/pages/documents/revisions? | |
| What support is required per task, label, language and relevant genre, and how much was collected in each split? | |
| Which numerical metrics, minimum support, abstention/coverage policy and failure rules were approved before tuning? | |
| Where is the approval record binding the exact input, labels, split map and target bytes to a real human decision? | |
| Who may access held-out labels, and what label-free input will each prediction author receive? | |
| Which rule baseline and optional candidate run IDs/configuration versions will use the same frozen input and split? | |

About 200 FR/EN queries is the initial query collection target from #6. It is not a minimum for every task or proof of adequate class support. Do not fill the worksheet with generated labels, model agreement, invented consent or demonstration threshold numbers. For implementation exercises use a separate corpus declared `synthetic`; its results remain release-ineligible.

## Freeze, run and review

1. Collect authorized anonymized cases and their original source references. For report packets, retain tool/request versions, effective site/property, requested and observed dates, timezone evidence, collection scope and missing/error states. Missing observations stay missing; a human review does not manufacture causal truth.
2. Have an annotator and a different human reviewer record labels and resolve disagreements using the approved taxonomy. Preserve uncertainty: use the task's `unclassified` or `unresolved` label when evidence is insufficient. Distinct identity strings do not prove genuine independent humans.
3. Review family assignments and keep each family in one partition before tuning. Query pair members must stay within their split. The validators catch declared family overlap; they cannot discover a paraphrase, translation or related event assigned to a different family.
4. Freeze exact input/label/split/target bytes and their hashes in the approved review record before tuning. The query manifest can bind its dataset hash and targets; `approved_by` and `frozen_before_tuning` are declarations, not authenticated approval or chronology. Keep held-out labels out of author inputs and record actual access/review evidence separately.
5. Run the best existing rules baseline and any optional candidate on the same input/split. Report observed errors, support, omissions and abstentions per task; keep cost, latency and calibration measurements separate. Only a human decision backed by the frozen targets can settle release readiness.

The [query schema and manifest guide](classifier-evaluation.md) provides the existing import contract. For a query evaluation, use actual supplied paths:

```sh
python3 scripts/eval_classifier.py \
  --dataset /absolute/authorized-query-corpus.json \
  --predictions /absolute/independent-held-out-predictions.json \
  --manifest /absolute/reviewed-pre-tuning-manifest.json
```

Those paths describe expected files; no authorized corpus or manifest is delivered by this worksheet. A successful process exit means the evaluator ran. It does not mean targets were met. The query release status remains `pending_human_review` for declared human data, or `ineligible_synthetic` for synthetic data, even if numerical targets are met.

For report review, `--prepare` produces observations without `claims`, annotation judgments or labels:

```sh
python3 scripts/eval_audit_reports.py \
  --dataset /absolute/authorized-report-corpus.json --prepare --split held_out
```

Keep that packet separate from the labeled corpus. A report author receives the observations; an independent human review must identify the candidate report's claims and retain their source references. The current evaluator does not consume prose or attach generated claims automatically. For frozen claim-label comparisons, prepare the supplied prediction contract below after that review, then run:

```sh
python3 scripts/eval_audit_reports.py \
  --dataset /absolute/authorized-report-corpus.json \
  --predictions /absolute/independent-claim-predictions.json
```

The prediction object has exactly `corpus_id`, `split`, `reviewer` and `predictions`; each row has exactly `case_id`, `claim_id` and `label`. IDs must refer to claims in the selected split. The `reviewer` identifier must differ from the annotation authors' declared metadata. It is an identity declaration, not proof of human authorship. Missing prediction rows reduce coverage; they do not become correct unresolved answers. To score a new report's claims, first establish independently reviewed claim records and their mapping rather than relabeling the candidate report as ground truth.

## Evidence required to finish #6

Before claiming human quality, retain the completed worksheet, actual authorization/review records, family-disjoint held-out corpus, genuine labels with disagreement history and numerical targets approved before tuning. Publish the task-specific held-out errors and support, including failures and unsupported measures. No authentic human corpus, approved numerical targets or human release decision is supplied by this intake, existing synthetic fixtures or declarative approval strings.
