# Query intent and pair evaluation

`scripts/eval_classifier.py` validates caller-supplied annotations and independent predictions, then reports their offline quality. It uses the Python standard library, imports no classifier and makes no API calls. Issue #6 stays open until authorized human FR/EN annotations, a frozen held-out corpus and agreed targets exist. The files under `tests/fixtures/classifier_eval/` are synthetic boundary examples and cannot satisfy that requirement.

## Annotation taxonomy: `query-intent-v1`

Label the result the searcher seeks. Question form alone does not determine intent.

| Intent label | Annotation rule |
| --- | --- |
| `informational` | Seeks an explanation, procedure or fact. |
| `navigational` | Seeks a named destination, account or known page. |
| `commercial` | Compares or evaluates options before choosing. |
| `transactional` | Seeks to buy, book, download or perform a concrete action. |
| `unclassified` | Context does not establish one intent, or competing intents remain unresolved. |

Preserve negation, qualifiers and the object of the query. “Where can I buy…” is a question with transactional intent. A comparison phrased without a question can still be commercial. Do not infer intent from punctuation or one trigger word. Annotators must distinguish a request to perform an action from a request to learn how it works.

Pair labels are `same_intent`, `distinct_intent` and `unclassified`. Judge whether the queries seek the same specific outcome, not merely whether both carry the broad `informational` label. Use `unclassified` when the relationship cannot be resolved. Retain `left_id` and `right_id`: “convert A to B” and “convert B to A” seek different directional outcomes. Reversing the order of those two query IDs does not reverse either query's meaning. The harness treats `(left_id, right_id)` as an ordered identity and permits its reverse as a separate annotation.

These definitions are the scaffold's taxonomy. The human review must approve and freeze them for #4/#5 before tuning. A taxonomy change needs a new version and corpus review; this harness currently accepts only `query-intent-v1`.

## Authorization, disagreement and splits

Use about 200 authorized, anonymized FR/EN queries for the issue's human corpus. Remove private domains, URLs, identifiers, email addresses and identifying free text before import. Keep the source authorization evidence in an approved location, and record a non-identifying reference in each annotation. Do not commit private source material or credentials.

A human annotator supplies the label; a human reviewer checks ambiguity and resolves disagreements. Record the resolution, including `no disagreement` when applicable. An agent or model proposing a label must not be its own ground-truth judge. Annotation metadata records assertions made by the caller. The CLI cannot establish consent, anonymization quality, reviewer identity, genuine human authorship or actual pre-tuning chronology.

Assign paraphrases, spelling variants, translations and related queries to one `family_id`. Keep each family in one split: `train`, `tuning` or `held_out`. Target roughly equal tuning and held-out halves for the initial corpus; `train` is available if the baseline needs it. Pair members must both occupy the pair's split. Related pairs need the same family assignment. The validator checks declared family IDs and pair references; humans must review the family mapping because it cannot discover undeclared semantic overlap.

Keep held-out labels separate from classifier inputs, prompts and tuning access. Prediction authors receive query IDs and text, or pair IDs and members, without labels or annotation judgments. An evaluator with authorized access joins predictions to the labels. The CLI's strict prediction schema rejects label fields but cannot prove a prediction author never saw ground truth.

## Dataset JSON schema

All fields below are required. Unknown fields, duplicate JSON object keys and duplicate IDs across both record arrays fail validation. IDs and references are nonempty strings. Use UTF-8 JSON, `schema_version: 1`, and one provenance per corpus: `human` or `synthetic`. Mixed corpora require separate files and reports.

```json
{
  "schema_version": 1,
  "corpus_id": "synthetic-schema-example",
  "taxonomy_version": "query-intent-v1",
  "provenance": "synthetic",
  "queries": [
    {
      "id": "q1",
      "family_id": "f1",
      "query": "comment comparer deux solutions",
      "language": "fr",
      "label": "commercial",
      "split": "held_out",
      "annotation": {
        "provenance": "synthetic",
        "annotator": "fixture-author",
        "reviewer": "fixture-reviewer",
        "source_authorization": "synthetic example authored for this guide",
        "disagreement_resolution": "controlled example, no human corpus"
      }
    },
    {
      "id": "q2",
      "family_id": "f1",
      "query": "how to compare two solutions",
      "language": "en",
      "label": "commercial",
      "split": "held_out",
      "annotation": {
        "provenance": "synthetic",
        "annotator": "fixture-author",
        "reviewer": "fixture-reviewer",
        "source_authorization": "synthetic example authored for this guide",
        "disagreement_resolution": "controlled example, no human corpus"
      }
    }
  ],
  "pairs": [
    {
      "id": "p1",
      "family_id": "pf1",
      "left_id": "q1",
      "right_id": "q2",
      "label": "same_intent",
      "split": "held_out",
      "annotation": {
        "provenance": "synthetic",
        "annotator": "fixture-author",
        "reviewer": "fixture-reviewer",
        "source_authorization": "synthetic example authored for this guide",
        "disagreement_resolution": "controlled example, no human corpus"
      }
    }
  ]
}
```

`queries` and `pairs` are arrays and may individually be empty. The selected task/split must contain at least one record. Query languages are `fr` or `en`. Every annotation field is a nonempty string and its provenance must equal the corpus provenance. Self-pairs, missing references, repeated ordered pairs and references crossing splits fail validation.

## Independent predictions JSON schema

Top-level fields are required. `task` is `intent` or `pairs`; `run_kind` is `rules` or `model`. The task and split select the evaluation set. Extra prediction IDs, IDs in another split and duplicate prediction IDs fail. Missing IDs and explicit `null` predictions count as abstentions.

```json
{
  "schema_version": 1,
  "corpus_id": "synthetic-schema-example",
  "run_id": "baseline-v1",
  "run_kind": "rules",
  "task": "intent",
  "split": "held_out",
  "predictions": [
    {
      "id": "q1",
      "predicted_label": "commercial",
      "confidence": 0.8,
      "cost_usd": 0.0,
      "latency_ms": 1.2,
      "scores": {
        "informational": 0.2,
        "navigational": 0.0,
        "commercial": 0.8,
        "transactional": 0.0,
        "unclassified": 0.0
      }
    },
    {"id": "q2", "predicted_label": null}
  ]
}
```

Each row requires only `id` and `predicted_label`. The four optional metadata fields shown above are the complete allowlist. Confidence and each score must be finite numbers in `[0, 1]`; cost and latency must be finite nonnegative numbers. Boolean values do not count as numbers. Scores require every label for the selected task, no others, and a sum of one within floating-point tolerance. Pair scores use the three pair labels. Scores describe the caller's distribution; the CLI does not replace or infer `predicted_label` from them.

Ground-truth fields such as `label`, `expected_label`, annotations or query text are rejected in prediction files. Model metadata remains optional so missing measurements are visible instead of invented. A model comparison needs complete observed cost, latency and probability scores before a release reviewer can assess it.

## Freeze the corpus and numerical targets before tuning

Save the final authorized dataset, compute its SHA-256, agree numerical targets for each task and record the approval reference in a separate manifest. Review and freeze the exact dataset and manifest bytes before tuning. Store the manifest in version control or another approved immutable review record. Changing whitespace in the dataset also changes its hash.

```sh
shasum -a 256 data/authorized-intents.v1.json
```

The following manifest shows the schema with demonstration targets. These numbers are not agreed release thresholds and must not be copied as an approval. `frozen_before_tuning` and `approved_by` are caller declarations that require human evidence.

```json
{
  "schema_version": 1,
  "corpus_id": "authorized-intents-v1",
  "taxonomy_version": "query-intent-v1",
  "dataset_sha256": "replace-with-exact-dataset-sha256",
  "frozen_before_tuning": true,
  "approved_by": "replace-with-actual-human-review-reference",
  "thresholds": {
    "intent": {
      "macro_precision": 0.8,
      "macro_recall": 0.8,
      "full_set_accuracy": 0.8,
      "coverage": 0.9,
      "min_support_per_class": 10
    },
    "pairs": {
      "macro_precision": 0.8,
      "macro_recall": 0.8,
      "full_set_accuracy": 0.8,
      "coverage": 0.9,
      "min_support_per_class": 10
    }
  }
}
```

Every supplied task target block requires all five fields. Quality and coverage targets are finite numbers in `[0, 1]`. Minimum support is a positive integer and applies to every taxonomy class, including `unclassified`. The selected task must have a target block; other task blocks are optional. The manifest must match corpus ID, taxonomy version and the exact dataset hash. The CLI rejects a manifest without a nonempty approval reference or with `frozen_before_tuning` other than `true`.

## Run and interpret the report

From the repository root, the supplied smoke fixture runs without packages or credentials:

```sh
python3 scripts/eval_classifier.py \
  --dataset tests/fixtures/classifier_eval/synthetic-boundary.json \
  --predictions tests/fixtures/classifier_eval/synthetic-predictions.json
```

Use your actual authorized files for a frozen held-out comparison:

```sh
python3 scripts/eval_classifier.py \
  --dataset data/authorized-intents.v1.json \
  --predictions data/baseline-intent.held-out.json \
  --manifest data/authorized-intents.v1.manifest.json > intent-report.json
```

Run pair predictions separately with `task: "pairs"` in their file. Run the best rule baseline and any optional model on the same frozen input and split. This harness does not run either baseline or model. Default pytest runs contract tests using synthetic data; it does not evaluate a real corpus or call a model.

The CLI writes JSON to stdout and returns zero when evaluation succeeds. Invalid input returns `2`, writes `invalid input:` to stderr and emits no report. A successful process exit means the evaluation ran, not that release targets were met.

Each class reports support, prediction count, true-positive count, precision and recall. Precision is `TP / predicted_count`; recall is `TP / support`. An undefined denominator contributes zero. Macro precision and recall average over all taxonomy classes, including classes with zero support. Full-set accuracy is correct predictions divided by the entire selected set. Coverage is non-null predictions divided by that set; abstention counts include missing rows. `unclassified` is an answered class, distinct from `null` abstention.

Cost totals and latency means cover only rows with caller-supplied measurements. Their `observed_count` and `missing_count` retain the full-set denominator; absent measurements produce JSON `null`, not zero. Calibration reports the mean multiclass Brier score, `sum((score - one_hot_label)^2)`, over rows with complete probability vectors, plus observed and missing counts. This is a probability error measure, not proof of calibration across real populations. Confidence alone cannot supply that measure.

`release_gate.threshold_assessment.status` is `not_supplied`, `not_held_out`, `met` or `not_met`. Supplied targets are checked only on `held_out`; each check and target appears in the report. Dataset and prediction hashes identify the exact bytes evaluated. A synthetic corpus always reports `release_gate.status: "ineligible_synthetic"`, even when targets are met. A declared human corpus reports `pending_human_review`; the CLI never approves a release. The reviewer must establish genuine labels, consent, split isolation, pre-tuning approval and the model's improvement over the best baseline. Real human inputs and agreed targets are still missing from this scaffold.

## Separate future evaluation tracks

The query corpus gates query intent/grouping in #4/#5. It does not validate these other tasks. Reuse validation patterns with task-specific schemas, corpora and targets; the current CLI accepts only `intent` and `pairs`.

| Future task | Required independent human labels and metrics |
| --- | --- |
| Editorial warnings, #17 and draft input #24 | Authorized FR/EN passages labeled acceptable, actionable or context-dependent by genre; per-rule precision, missed actionable warnings, genre support and disagreements. HTML fixtures establish implementation behavior only. |
| Rewrite fidelity, #20 | Original/revision pairs reviewed for numbers, units, dates, links, negation, modality, referents, scope and causality. Report mechanical literal checks separately from semantic review; the rewriting agent cannot judge its own ground truth. |
| Page similarity, #22 | Page-pair judgments covering shared templates, translations and valid local-service overlap. Candidate similarity does not establish cannibalization or authorize merging/deleting pages. |
| Instruction detection and readiness | Separate page-level positive/benign corpora and task labels. Query or editorial labels cannot validate injection detection or citation probability. |

Freeze related page, document and revision families within one split for each track. Record authorization, anonymization, provenance, disagreements and numerical targets before tuning. Keep task reports separate so an aggregate cannot conceal a weak task. Model integration remains optional.

## Audit evidence tracks: preparation for #6

The following protocols prepare #38/#39/#40/#41/#45/#46. They do not add new tasks to `scripts/eval_classifier.py`, supply human labels or approve a release. Use a separate adapter and report for each task once its authorized corpus and frozen targets exist.

| Track | Case coverage | Review question | Measures to freeze before tuning |
| --- | --- | --- | --- |
| Traffic diagnosis | Reporting lag, missing rows, observed zero, historical spikes, seasonal references, collection incidents and caller-declared changes | Which claim is supported by this packet, which is a hypothesis, and which requires abstention? Do not invent the true cause. | Unsupported-claim rate, evidence preservation, justified abstention and support by case family |
| Harmful competition | Legitimate category/product results, distinct intent/market, navigational queries, migration and material URL alternation | Does the supplied evidence justify further review or a conditional change? Shared queries alone do not justify consolidation. | False consolidation proposals, missed review candidates, unknown-intent handling and family support |
| Main-content extraction | Authorized FR/EN article, product, local-service, forum and JS-shell pages with independently marked template/content boundaries | Which source spans belong in the task's content sample? The candidate extractor cannot supply its own labels. | Included template spans, omitted useful spans, unsupported inputs and downstream warning changes |
| Report fidelity | Multi-property packets, incompatible windows, partial providers, unknown indexing, contradictory observations and bounded output | Does each report claim retain the correct source and uncertainty? Model agreement does not supply a human label. | Source/window mismatches, unavailable-to-zero coercions, unsupported claims, and omissions disclosed by count/reason |

### Packet and review protocol

1. Freeze a case packet with its exact tool/request versions, effective site/property, requested and observed dates, source observations, missing/error states, collection scope and source authorization reference. Preserve the original packet hash outside any derived report. Remove private identifying content before committing a packet.
2. Record the track, language and a family/split assignment. Keep the same property/event/page and related revisions in one family so nearby observations do not leak into held-out evaluation. A human reviewer must check this assignment; declaring a family is not proof of isolation.
3. For each report claim, ask a human annotator to identify supporting observation references and classify it as supported, unsupported or unresolved from the supplied packet. A second human reviewer records disagreements and their resolution. Record observations separately from the unknown underlying cause.
4. Freeze the approved packet bytes, label definitions, task-specific numerical targets and reviewer approval reference before tuning. Missing targets or reviewed labels keep the quality gate pending; synthetic expected outputs remain implementation checks.
5. Give the report author the observations without held-out labels. An evaluator joins the report and independent judgments. Report counts and undefined denominators explicitly; no single combined score may hide a weak track.

### Controlled implementation cases

The first implementation checks can use synthetic packets: generic search-appearance rows with no verified AI identification; a traffic-concentration alert with no manual-action observation; a legitimate multi-URL query with unknown intent; and a missing inspection alongside measured zero clicks. Their expected boundary is that these observations cannot become an AI-loss estimate, penalty claim, unconditional merge, or unindexed verdict respectively.

These are proposed case families, not collected human examples or executed agent trials. Routing/BM25 scores, mocked-client tests and a model's self-check do not establish report accuracy. Preparing this protocol leaves #6 open for authorized task-specific data, independent reviewed labels and pre-tuning targets.
