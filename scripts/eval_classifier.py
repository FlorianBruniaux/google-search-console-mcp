#!/usr/bin/env python3
"""Evaluate caller-supplied query predictions offline, without importing a classifier."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


LABELS = {
    "intent": ("informational", "navigational", "commercial", "transactional", "unclassified"),
    "pairs": ("same_intent", "distinct_intent", "unclassified"),
}
SPLITS = ("train", "tuning", "held_out")
ANNOTATION_FIELDS = {"provenance", "annotator", "reviewer", "source_authorization",
                     "disagreement_resolution"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def shape(value, required, optional=()):
    require(isinstance(value, dict), "expected an object")
    require(set(value) >= set(required), "missing required fields")
    require(set(value) <= set(required) | set(optional), "unknown fields")


def nonempty(value):
    require(isinstance(value, str) and bool(value.strip()), "expected a nonempty string")


def choice(value, allowed):
    require(isinstance(value, str) and value in allowed, "unknown categorical value")


def number(value, maximum=None):
    require(type(value) in (int, float), "expected a number")
    require(math.isfinite(value) and value >= 0, "expected a finite nonnegative number")
    require(maximum is None or value <= maximum, "number exceeds permitted maximum")


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON object key")
        result[key] = value
    return result


def load_json(path):
    raw = Path(path).read_bytes()
    return json.loads(raw, object_pairs_hook=unique_keys), hashlib.sha256(raw).hexdigest()


def validate_dataset(data):
    shape(data, {"schema_version", "corpus_id", "taxonomy_version", "provenance", "queries", "pairs"})
    require(type(data["schema_version"]) is int and data["schema_version"] == 1, "unsupported schema")
    nonempty(data["corpus_id"])
    require(data["taxonomy_version"] == "query-intent-v1", "unsupported taxonomy")
    choice(data["provenance"], ("human", "synthetic"))
    identities, families, queries, pair_identities = set(), {}, {}, set()
    for task, collection in (("intent", "queries"), ("pairs", "pairs")):
        require(isinstance(data[collection], list), "expected a record array")
        for row in data[collection]:
            fields = {"id", "family_id", "label", "split", "annotation"}
            fields |= {"query", "language"} if task == "intent" else {"left_id", "right_id"}
            shape(row, fields)
            for field in ("id", "family_id"):
                nonempty(row[field])
            require(row["id"] not in identities, "duplicate record identity")
            identities.add(row["id"])
            choice(row["label"], LABELS[task])
            choice(row["split"], SPLITS)
            previous = families.setdefault(row["family_id"], row["split"])
            require(previous == row["split"], "family overlaps splits")
            shape(row["annotation"], ANNOTATION_FIELDS)
            for field in ANNOTATION_FIELDS:
                nonempty(row["annotation"][field])
            require(row["annotation"]["provenance"] == data["provenance"], "provenance mismatch")
            if task == "intent":
                nonempty(row["query"])
                choice(row["language"], ("fr", "en"))
                queries[row["id"]] = row
            else:
                for field in ("left_id", "right_id"):
                    nonempty(row[field])
                    require(row[field] in queries, "pair references an unknown query")
                    require(queries[row[field]]["split"] == row["split"], "pair crosses splits")
                require(row["left_id"] != row["right_id"], "self pair")
                identity = (row["left_id"], row["right_id"])
                require(identity not in pair_identities, "duplicate ordered pair")
                pair_identities.add(identity)


def validate_predictions(data, prediction_file):
    shape(prediction_file, {"schema_version", "corpus_id", "run_id", "run_kind", "task", "split", "predictions"})
    require(type(prediction_file["schema_version"]) is int and prediction_file["schema_version"] == 1,
            "unsupported prediction schema")
    require(prediction_file["corpus_id"] == data["corpus_id"], "corpus mismatch")
    nonempty(prediction_file["run_id"])
    choice(prediction_file["run_kind"], ("rules", "model"))
    choice(prediction_file["task"], LABELS)
    choice(prediction_file["split"], SPLITS)
    task = prediction_file["task"]
    collection = "queries" if task == "intent" else "pairs"
    selected = [row for row in data[collection] if row["split"] == prediction_file["split"]]
    require(bool(selected), "selected task/split is empty")
    allowed_ids = {row["id"] for row in selected}
    require(isinstance(prediction_file["predictions"], list), "expected a prediction array")
    predicted = {}
    for row in prediction_file["predictions"]:
        shape(row, {"id", "predicted_label"}, {"confidence", "cost_usd", "latency_ms", "scores"})
        nonempty(row["id"])
        require(row["id"] in allowed_ids, "prediction outside selected task/split")
        require(row["id"] not in predicted, "duplicate prediction identity")
        if row["predicted_label"] is not None:
            choice(row["predicted_label"], LABELS[task])
        for field in ("confidence", "cost_usd", "latency_ms"):
            if field in row:
                number(row[field], 1 if field == "confidence" else None)
        if "scores" in row:
            shape(row["scores"], LABELS[task])
            for value in row["scores"].values():
                number(value, 1)
            require(math.isclose(sum(row["scores"].values()), 1, abs_tol=1e-9), "scores must sum to one")
        predicted[row["id"]] = row
    return selected, predicted


def metrics_for(rows, predicted, labels):
    per_class = {}
    for label in labels:
        support = sum(row["label"] == label for row in rows)
        predicted_count = sum(row["predicted_label"] == label for row in predicted.values())
        true_positive = sum(row["label"] == label and
                            predicted.get(row["id"], {}).get("predicted_label") == label for row in rows)
        per_class[label] = {
            "support": support, "predicted_count": predicted_count,
            "true_positive_count": true_positive,
            "precision": true_positive / predicted_count if predicted_count else 0.0,
            "recall": true_positive / support if support else 0.0,
        }
    count = len(rows)
    answered = sum(row["predicted_label"] is not None for row in predicted.values())
    correct = sum(value["true_positive_count"] for value in per_class.values())
    return {
        "sample_count": count, "correct_count": correct,
        "full_set_accuracy": correct / count, "coverage": answered / count,
        "abstention_count": count - answered, "abstention_rate": (count - answered) / count,
        "macro_precision": sum(value["precision"] for value in per_class.values()) / len(labels),
        "macro_recall": sum(value["recall"] for value in per_class.values()) / len(labels),
        "per_class": per_class,
    }


def prediction_metadata(rows, predicted, labels):
    costs = [row["cost_usd"] for row in predicted.values() if "cost_usd" in row]
    latencies = [row["latency_ms"] for row in predicted.values() if "latency_ms" in row]
    brier = []
    for row in rows:
        scores = predicted.get(row["id"], {}).get("scores")
        if scores is not None:
            brier.append(sum((scores[label] - int(label == row["label"])) ** 2 for label in labels))
    count = len(rows)
    return {
        "cost_usd": {"observed_total": sum(costs) if costs else None,
                     "observed_count": len(costs), "missing_count": count - len(costs)},
        "latency_ms": {"observed_mean": sum(latencies) / len(latencies) if latencies else None,
                       "observed_count": len(latencies), "missing_count": count - len(latencies)},
        "calibration": {"brier_score": sum(brier) / len(brier) if brier else None,
                        "observed_count": len(brier), "missing_count": count - len(brier)},
    }


def assess_thresholds(manifest, data, dataset_sha, task, split, metrics):
    if manifest is None:
        return {"status": "not_supplied"}
    shape(manifest, {"schema_version", "corpus_id", "taxonomy_version", "dataset_sha256",
                     "frozen_before_tuning", "approved_by", "thresholds"})
    require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1,
            "unsupported manifest schema")
    require(manifest["corpus_id"] == data["corpus_id"], "manifest corpus mismatch")
    require(manifest["taxonomy_version"] == data["taxonomy_version"], "manifest taxonomy mismatch")
    require(manifest["dataset_sha256"] == dataset_sha, "frozen dataset hash mismatch")
    require(manifest["frozen_before_tuning"] is True, "manifest must be frozen before tuning")
    nonempty(manifest["approved_by"])
    shape(manifest["thresholds"], (), LABELS)
    require(task in manifest["thresholds"], "manifest missing selected task targets")
    fields = {"macro_precision", "macro_recall", "full_set_accuracy", "coverage", "min_support_per_class"}
    for targets in manifest["thresholds"].values():
        shape(targets, fields)
        for field in fields - {"min_support_per_class"}:
            number(targets[field], 1)
        require(type(targets["min_support_per_class"]) is int and targets["min_support_per_class"] >= 1,
                "support target must be a positive integer")
    if split != "held_out":
        return {"status": "not_held_out"}
    targets = manifest["thresholds"][task]
    checks = {field: metrics[field] >= targets[field] for field in fields - {"min_support_per_class"}}
    checks["min_support_per_class"] = all(
        value["support"] >= targets["min_support_per_class"] for value in metrics["per_class"].values())
    return {"status": "met" if all(checks.values()) else "not_met", "checks": checks, "targets": targets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--manifest")
    args = parser.parse_args()
    try:
        data, dataset_sha = load_json(args.dataset)
        prediction_file, prediction_sha = load_json(args.predictions)
        validate_dataset(data)
        rows, predicted = validate_predictions(data, prediction_file)
        manifest = load_json(args.manifest)[0] if args.manifest else None
        labels = LABELS[prediction_file["task"]]
        metrics = metrics_for(rows, predicted, labels)
        report = {
            "schema_version": 1, "corpus_id": data["corpus_id"],
            "provenance": data["provenance"], "dataset_sha256": dataset_sha,
            "predictions_sha256": prediction_sha, "run_id": prediction_file["run_id"],
            "task": prediction_file["task"], "split": prediction_file["split"],
            "run_kind": prediction_file["run_kind"],
            "metrics": metrics,
            "prediction_metadata": prediction_metadata(rows, predicted, labels),
            "release_gate": {"status": "ineligible_synthetic" if data["provenance"] == "synthetic"
                             else "pending_human_review",
                             "threshold_assessment": assess_thresholds(
                                 manifest, data, dataset_sha, prediction_file["task"],
                                 prediction_file["split"], metrics)},
        }
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    except (ValueError, OSError, OverflowError) as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
