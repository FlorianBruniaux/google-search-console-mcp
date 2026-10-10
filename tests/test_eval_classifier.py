"""Offline CLI contract; fixtures below are synthetic, never release evidence."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "eval_classifier.py"


def annotation(provenance="synthetic"):
    return {
        "provenance": provenance,
        "annotator": "fixture-author",
        "reviewer": "fixture-reviewer",
        "source_authorization": "synthetic examples authored for tests",
        "disagreement_resolution": "no disagreement in controlled fixture",
    }


def dataset():
    labels = ["informational", "informational", "commercial", "unclassified",
              "navigational", "transactional", "informational"]
    return {
        "schema_version": 1,
        "corpus_id": "synthetic-boundary-fixture",
        "taxonomy_version": "query-intent-v1",
        "provenance": "synthetic",
        "queries": [
            {"id": f"q{i}", "family_id": f"f{i}", "query": f"synthetic query {i}",
             "language": "fr" if i % 2 else "en", "label": label,
             "split": "tuning" if i == 7 else "held_out", "annotation": annotation()}
            for i, label in enumerate(labels, 1)
        ],
        "pairs": [
            {"id": "p1", "family_id": "pf1", "left_id": "q1", "right_id": "q2",
             "label": "same_intent", "split": "held_out", "annotation": annotation()},
            {"id": "p2", "family_id": "pf2", "left_id": "q4", "right_id": "q5",
             "label": "unclassified", "split": "held_out", "annotation": annotation()},
        ],
    }


def predictions():
    return {
        "schema_version": 1, "corpus_id": "synthetic-boundary-fixture",
        "run_id": "boundary-rules", "run_kind": "rules", "task": "intent",
        "split": "held_out",
        "predictions": [
            {"id": "q1", "predicted_label": "informational"},
            {"id": "q2", "predicted_label": "commercial"},
            {"id": "q4", "predicted_label": "unclassified"},
            {"id": "q6", "predicted_label": "transactional"},
        ],
    }


def run_cli(tmp_path, data=None, predicted=None, manifest=None):
    data = dataset() if data is None else data
    predicted = predictions() if predicted is None else predicted
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(data), encoding="utf-8")
    prediction_path = tmp_path / "predictions.json"
    prediction_path.write_text(json.dumps(predicted), encoding="utf-8")
    args = [sys.executable, "-I", str(SCRIPT), "--dataset", str(dataset_path),
            "--predictions", str(prediction_path)]
    if manifest is not None:
        frozen = copy.deepcopy(manifest)
        if frozen.get("dataset_sha256") == "AUTO":
            frozen["dataset_sha256"] = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(frozen), encoding="utf-8")
        args += ["--manifest", str(manifest_path)]
    return subprocess.run(args, capture_output=True, text=True, check=False)


def test_full_set_metrics_include_missing_predictions_and_unclassified(tmp_path):
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["metrics"]["sample_count"] == 6
    assert report["metrics"]["correct_count"] == 3
    assert report["metrics"]["full_set_accuracy"] == 0.5
    assert report["metrics"]["coverage"] == pytest.approx(2 / 3)
    assert report["metrics"]["abstention_count"] == 2
    assert report["metrics"]["macro_precision"] == 0.6
    assert report["metrics"]["macro_recall"] == 0.5
    assert report["metrics"]["per_class"]["informational"] == {
        "support": 2, "predicted_count": 1, "true_positive_count": 1,
        "precision": 1.0, "recall": 0.5,
    }
    assert report["metrics"]["per_class"]["unclassified"]["support"] == 1
    assert report["release_gate"]["status"] == "ineligible_synthetic"


def test_pairs_have_separate_metrics_and_explicit_abstention(tmp_path):
    predicted = predictions()
    predicted.update(task="pairs", predictions=[
        {"id": "p1", "predicted_label": "distinct_intent"},
        {"id": "p2", "predicted_label": None},
    ])
    result = run_cli(tmp_path, predicted=predicted)
    assert result.returncode == 0, result.stderr
    metrics = json.loads(result.stdout)["metrics"]
    assert metrics["sample_count"] == 2
    assert metrics["full_set_accuracy"] == 0
    assert metrics["coverage"] == 0.5
    assert metrics["abstention_count"] == 1
    assert set(metrics["per_class"]) == {"same_intent", "distinct_intent", "unclassified"}


@pytest.mark.parametrize("collection", ["queries", "pairs"])
@pytest.mark.parametrize("provenance", ["human", "synthetic"])
def test_self_reviewed_annotations_fail_before_scoring(tmp_path, collection, provenance):
    data = dataset()
    data["provenance"] = provenance
    for row in data["queries"] + data["pairs"]:
        row["annotation"] = annotation(provenance)
    row = data[collection][0]
    row["annotation"]["reviewer"] = row["annotation"]["annotator"]
    result = run_cli(tmp_path, data=data)
    assert result.returncode == 2, result.stderr
    assert "independent annotation review required" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("mutation", [
    "query_duplicate", "pair_duplicate", "cross_task_duplicate", "family_leak",
    "pair_reference_missing", "pair_cross_split", "pair_self", "pair_identity_duplicate",
    "unknown_intent", "unknown_pair_label", "unknown_language", "unknown_split",
    "provenance_mismatch", "empty_consent", "missing_review", "empty_query",
])
def test_invalid_annotations_fail_before_scoring(tmp_path, mutation):
    data = dataset()
    if mutation == "query_duplicate":
        data["queries"].append(copy.deepcopy(data["queries"][0]))
    elif mutation == "pair_duplicate":
        data["pairs"].append(copy.deepcopy(data["pairs"][0]))
    elif mutation == "cross_task_duplicate":
        data["pairs"][0]["id"] = "q1"
    elif mutation == "family_leak":
        data["queries"][-1]["family_id"] = "f1"
    elif mutation == "pair_reference_missing":
        data["pairs"][0]["left_id"] = "absent"
    elif mutation == "pair_cross_split":
        data["pairs"][0]["right_id"] = "q7"
    elif mutation == "pair_self":
        data["pairs"][0]["right_id"] = "q1"
    elif mutation == "pair_identity_duplicate":
        duplicate = copy.deepcopy(data["pairs"][0])
        duplicate["id"] = "p3"
        data["pairs"].append(duplicate)
    elif mutation == "unknown_intent":
        data["queries"][0]["label"] = "invented"
    elif mutation == "unknown_pair_label":
        data["pairs"][0]["label"] = "merge_pages"
    elif mutation == "unknown_language":
        data["queries"][0]["language"] = "de"
    elif mutation == "unknown_split":
        data["queries"][0]["split"] = "validation"
    elif mutation == "provenance_mismatch":
        data["queries"][0]["annotation"]["provenance"] = "human"
    elif mutation == "empty_consent":
        data["queries"][0]["annotation"]["source_authorization"] = ""
    elif mutation == "missing_review":
        del data["queries"][0]["annotation"]["reviewer"]
    elif mutation == "empty_query":
        data["queries"][0]["query"] = "  "
    result = run_cli(tmp_path, data=data)
    assert result.returncode == 2, result.stderr
    assert "invalid input:" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("mutation", [
    "duplicate", "extra", "outside_split", "unknown_label", "ground_truth",
    "nan", "infinite", "negative_cost", "bad_confidence", "bad_scores",
    "wrong_corpus", "unknown_field",
])
def test_invalid_independent_predictions_are_rejected(tmp_path, mutation):
    predicted = predictions()
    row = predicted["predictions"][0]
    if mutation == "duplicate":
        predicted["predictions"].append(copy.deepcopy(row))
    elif mutation == "extra":
        row["id"] = "absent"
    elif mutation == "outside_split":
        row["id"] = "q7"
    elif mutation == "unknown_label":
        row["predicted_label"] = "invented"
    elif mutation == "ground_truth":
        row["label"] = "informational"
    elif mutation == "nan":
        row["confidence"] = float("nan")
    elif mutation == "infinite":
        row["latency_ms"] = float("inf")
    elif mutation == "negative_cost":
        row["cost_usd"] = -1
    elif mutation == "bad_confidence":
        row["confidence"] = 1.1
    elif mutation == "bad_scores":
        row["scores"] = {"informational": 1.0}
    elif mutation == "wrong_corpus":
        predicted["corpus_id"] = "another-corpus"
    elif mutation == "unknown_field":
        predicted["human_labels"] = []
    result = run_cli(tmp_path, predicted=predicted)
    assert result.returncode == 2, result.stderr
    assert "invalid input:" in result.stderr
    assert result.stdout == ""


def frozen_manifest():
    return {
        "schema_version": 1, "corpus_id": "synthetic-boundary-fixture",
        "taxonomy_version": "query-intent-v1", "dataset_sha256": "AUTO",
        "frozen_before_tuning": True, "approved_by": "fixture-reviewer",
        "thresholds": {"intent": {
            "macro_precision": 0.5, "macro_recall": 0.4, "full_set_accuracy": 0.4,
            "coverage": 0.6, "min_support_per_class": 1,
        }},
    }


def test_synthetic_fixture_cannot_pass_human_gate_even_when_targets_met(tmp_path):
    result = run_cli(tmp_path, manifest=frozen_manifest())
    assert result.returncode == 0, result.stderr
    gate = json.loads(result.stdout)["release_gate"]
    assert gate["status"] == "ineligible_synthetic"
    assert gate["threshold_assessment"]["status"] == "met"
    assert gate["threshold_assessment"]["checks"]["coverage"] is True


def test_human_declarations_and_met_targets_still_require_human_release_review(tmp_path):
    data = dataset()
    data["provenance"] = "human"
    for row in data["queries"] + data["pairs"]:
        row["annotation"] = annotation("human")
    result = run_cli(tmp_path, data=data, manifest=frozen_manifest())
    assert result.returncode == 0, result.stderr
    gate = json.loads(result.stdout)["release_gate"]
    assert gate["status"] == "pending_human_review"
    assert gate["threshold_assessment"]["status"] == "met"


def test_threshold_failure_and_absent_manifest_are_visible(tmp_path):
    manifest = frozen_manifest()
    manifest["thresholds"]["intent"]["coverage"] = 0.9
    result = run_cli(tmp_path, manifest=manifest)
    assert result.returncode == 0, result.stderr
    gate = json.loads(result.stdout)["release_gate"]
    assert gate["threshold_assessment"]["status"] == "not_met"
    assert gate["threshold_assessment"]["checks"]["coverage"] is False
    result = run_cli(tmp_path)
    assert json.loads(result.stdout)["release_gate"]["threshold_assessment"]["status"] == "not_supplied"


@pytest.mark.parametrize("mutation", [
    "wrong_hash", "wrong_corpus", "unfrozen", "missing_approval", "missing_target",
    "nan_target", "out_of_range", "fractional_support", "boolean_target", "wrong_task",
])
def test_unfrozen_or_invalid_targets_are_rejected(tmp_path, mutation):
    manifest = frozen_manifest()
    targets = manifest["thresholds"]["intent"]
    if mutation == "wrong_hash":
        manifest["dataset_sha256"] = "a" * 64
    elif mutation == "wrong_corpus":
        manifest["corpus_id"] = "another-corpus"
    elif mutation == "unfrozen":
        manifest["frozen_before_tuning"] = False
    elif mutation == "missing_approval":
        manifest["approved_by"] = ""
    elif mutation == "missing_target":
        del targets["macro_recall"]
    elif mutation == "nan_target":
        targets["coverage"] = float("nan")
    elif mutation == "out_of_range":
        targets["coverage"] = 2.0
    elif mutation == "fractional_support":
        targets["min_support_per_class"] = 0.5
    elif mutation == "boolean_target":
        targets["coverage"] = True
    elif mutation == "wrong_task":
        manifest["thresholds"] = {"editorial": targets}
    result = run_cli(tmp_path, manifest=manifest)
    assert result.returncode == 2, result.stderr
    assert "invalid input:" in result.stderr
    assert result.stdout == ""


def test_model_metadata_reports_partial_cost_latency_and_score_calibration(tmp_path):
    predicted = predictions()
    predicted["run_kind"] = "model"
    row = predicted["predictions"][0]
    row.update(cost_usd=0.01, latency_ms=12, scores={
        "informational": 0.8, "navigational": 0.1, "commercial": 0.1,
        "transactional": 0.0, "unclassified": 0.0,
    })
    result = run_cli(tmp_path, predicted=predicted)
    assert result.returncode == 0, result.stderr
    metadata = json.loads(result.stdout)["prediction_metadata"]
    assert metadata["cost_usd"] == {"observed_total": 0.01, "observed_count": 1, "missing_count": 5}
    assert metadata["latency_ms"] == {"observed_mean": 12.0, "observed_count": 1, "missing_count": 5}
    assert metadata["calibration"]["brier_score"] == pytest.approx(0.06)
    assert metadata["calibration"]["observed_count"] == 1
    assert metadata["calibration"]["missing_count"] == 5


def test_absent_model_metadata_is_unknown_not_zero(tmp_path):
    predicted = predictions()
    predicted["run_kind"] = "model"
    result = run_cli(tmp_path, predicted=predicted)
    assert result.returncode == 0, result.stderr
    metadata = json.loads(result.stdout)["prediction_metadata"]
    assert metadata["cost_usd"]["observed_total"] is None
    assert metadata["latency_ms"]["observed_mean"] is None
    assert metadata["calibration"]["brier_score"] is None
    assert metadata["calibration"]["missing_count"] == 6
