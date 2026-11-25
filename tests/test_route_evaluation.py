"""Synthetic cohorts test evaluator behavior; none of these are physical outcome data."""
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from nagdiff.route_evaluation import brier_threshold, design, evaluate, freeze, main


def plan():
    return {
        "protocol_id": "synthetic-protocol", "cohort_design": "all_enrolled",
        "enrollment_source": "synthetic roster before observation",
        "feature_source": "synthetic training-only priors and observables",
        "model": {"energy_unit": "pJ", "energy_reference": 2, "temperature": 1,
                  "alpha": 1, "beta": 0, "gamma": 0, "delta": 1e-12},
        "conditions": [{
            "condition_id": "synthetic-A", "window": "0-100 ps", "run_ids": ["a", "b", "c", "d"],
            "routes": {
                "collapse": {"barrier": 0, "observable_mismatch": 1, "prior_probability": 0.5,
                             "topology_penalty": 0},
                "escape": {"barrier": 2, "observable_mismatch": 0, "prior_probability": 0.5,
                           "topology_penalty": 0},
            },
        }],
    }


def outcomes():
    return {"protocol_id": "synthetic-protocol", "outcome_source": "synthetic held-out adjudication",
            "records": [{"condition_id": "synthetic-A", "window": "0-100 ps", "run_id": run, "outcome": label}
                        for run, label in zip("abcd", ["escape", "collapse", "censored", "indeterminate"])]}


def encode(obj):
    return json.dumps(obj).encode()


def scored(p, y):
    snapshot = freeze(encode(p))
    return evaluate(snapshot, hashlib.sha256(snapshot).hexdigest(), encode(y))


class TestRoutes(unittest.TestCase):
    def test_original_v1_snapshot_replays_and_supports_outcome_blind_design(self):
        raw = freeze(encode(plan()))
        # Digest of the same fixture as frozen by the original v1 implementation.
        digest = "5cd2659dbfc6b66c8b2a14b261434f2c9f8a42128973529a9c5a69d93e390476"
        self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
        details = design(raw, digest)["conditions"]["synthetic-A"]
        self.assertEqual(details["enrolled"], 4)
        self.assertEqual(details["brier_threshold"]["full_has_lower_loss_when"], "above_threshold")
        result = evaluate(raw, digest, encode(outcomes()))
        for key, value in details.items():
            self.assertEqual(value, result["by_condition"]["synthetic-A"][key])
        self.assertEqual(result["equal_condition"]["mean_brier"], result["mean_brier"])
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            design(raw + b" ", digest)

    def test_threshold_matches_empirical_binary_brier_in_either_direction(self):
        for full, barrier, direction in ((0.75, 0.25, "above_threshold"), (0.25, 0.75, "below_threshold")):
            diagnostic = brier_threshold(full, barrier)
            self.assertEqual(diagnostic["escape_fraction_at_tie_exact"], "1/2")
            self.assertEqual(diagnostic["full_has_lower_loss_when"], direction)
            self.assertEqual(diagnostic["tie"], "at_threshold")
            for escape in range(5):
                q = escape / 4
                losses = [sum((p - y) ** 2 for y in [1] * escape + [0] * (4 - escape)) / 4
                          for p in (full, barrier)]
                self.assertEqual(losses[0] == losses[1], q == 0.5)
                self.assertEqual(losses[0] < losses[1], q > 0.5 if full > barrier else q < 0.5)
        equal = brier_threshold(0.25, 0.25)
        self.assertEqual(equal["tie"], "every_escape_fraction")
        self.assertEqual(equal["full_has_lower_loss_when"], "never")
        self.assertIsNone(equal["escape_fraction_at_tie"])
        self.assertEqual(brier_threshold(1, math.nextafter(1.0, 0.0))["escape_fraction_at_tie_exact"],
                         "18014398509481983/18014398509481984")
        for bad in (True, None, float("nan"), -0.1, 1.1):
            with self.assertRaises(ValueError):
                brier_threshold(bad, 0.5)

    def test_differential_resolution_reverses_equal_condition_comparison(self):
        p = plan()
        a = p["conditions"][0]
        a["run_ids"] = [f"run-{i}" for i in range(9)]
        a["routes"]["escape"]["barrier"] = 0
        a["routes"]["collapse"]["observable_mismatch"] = math.log(1.5)
        b = copy.deepcopy(a)
        b["condition_id"] = "synthetic-B"
        b["routes"]["collapse"]["observable_mismatch"] = math.log(9)
        p["conditions"].append(b)
        y = outcomes()
        y["records"] = [
            {"condition_id": c["condition_id"], "window": c["window"], "run_id": run, "outcome": label}
            for c, labels in [(a, ["escape"] * 9), (b, ["collapse"] + ["censored"] * 8)]
            for run, label in zip(c["run_ids"], labels)
        ]
        out = scored(p, y)
        a_result, b_result = (out["by_condition"][c["condition_id"]] for c in (a, b))
        self.assertEqual((a_result["resolved"], b_result["resolved"]), (9, 1))
        self.assertEqual(b_result["outcome_counts"]["censored"], 8)
        self.assertEqual((a_result["observed_escape_fraction"], b_result["observed_escape_fraction"]), (1, 0))
        self.assertAlmostEqual(a_result["mean_full_minus_barrier_only"], -0.09)
        self.assertAlmostEqual(b_result["mean_full_minus_barrier_only"], 0.56)
        self.assertAlmostEqual(out["mean_full_minus_barrier_only"], -0.025)
        self.assertAlmostEqual(out["equal_condition"]["mean_full_minus_barrier_only"], 0.235)
        self.assertAlmostEqual(out["equal_condition"]["mean_brier"]["full"], 0.485)
        self.assertAlmostEqual(out["equal_condition"]["mean_brier"]["barrier_only"], 0.25)
        y["records"][9]["outcome"] = "indeterminate"
        missing = scored(p, y)
        self.assertAlmostEqual(missing["mean_full_minus_barrier_only"], -0.09)
        self.assertEqual(missing["equal_condition"]["conditions_without_resolved_events"], ["synthetic-B"])
        self.assertEqual(missing["equal_condition"]["mean_brier"], {"barrier_only": None, "full": None})
        self.assertIsNone(missing["equal_condition"]["mean_full_minus_barrier_only"])
        self.assertIsNone(missing["by_condition"]["synthetic-B"]["observed_escape_fraction"])

    def test_pin_does_not_bypass_snapshot_schema_checks(self):
        for key, value in (("schema_version", True), ("schema_version", 1.0), ("plan_sha256", "bad"),
                           ("protocol_id", []), ("enrollment_source", None), ("feature_source", ""),
                           ("model", {"energy_reference": 0}), ("conditions", {})):
            with self.subTest(key=key, value=value):
                snap = json.loads(freeze(encode(plan())))
                snap[key] = value
                raw = encode(snap)
                digest = hashlib.sha256(raw).hexdigest()
                with self.assertRaises(ValueError):
                    design(raw, digest)
                with self.assertRaises(ValueError):
                    evaluate(raw, digest, encode(outcomes()))

    def test_known_binary_brier_and_coverage(self):
        out = scored(plan(), outcomes())
        barrier = 1 / (1 + math.exp(1))
        loss = ((1 - barrier) ** 2 + barrier ** 2) / 2
        self.assertAlmostEqual(out["mean_brier"]["full"], 0.25)
        self.assertAlmostEqual(out["mean_brier"]["barrier_only"], loss)
        self.assertAlmostEqual(out["mean_full_minus_barrier_only"], 0.25 - loss)
        self.assertEqual([r["run_id"] for r in out["paired_runs"]], ["a", "b"])
        self.assertEqual(out["resolved_fraction"], 0.5)
        self.assertEqual(out["outcome_counts"], dict(escape=1, collapse=1, indeterminate=1, censored=1))

    def test_units_change_together_and_results_are_row_order_independent(self):
        p, y = plan(), outcomes()
        baseline = scored(p, y)
        p["model"].update(energy_unit="J", energy_reference=2e-12)
        p["conditions"][0]["routes"]["escape"]["barrier"] = 2e-12
        y["records"].reverse()
        self.assertEqual(scored(p, y)["mean_brier"], baseline["mean_brier"])

    def test_declared_units_follow_extractor(self):
        for unit in ("J", "pJ", "µJ", "meV", "10^-16 J"):
            with self.subTest(unit=unit):
                p = plan()
                p["model"]["energy_unit"] = unit
                self.assertEqual(json.loads(freeze(encode(p)))["model"]["energy_unit"], unit)
        for unit in ("", "  ", None, "1", "banana", "J/m^3", "J or pJ"):
            with self.subTest(unit=unit):
                p = plan()
                p["model"]["energy_unit"] = unit
                with self.assertRaises(ValueError):
                    freeze(encode(p))

    def test_model_bounds_and_intermediate_overflow(self):
        for field in ("energy_reference", "delta", "temperature"):
            for value in (0, -1):
                with self.subTest(field=field, value=value):
                    p = plan()
                    p["model"][field] = value
                    with self.assertRaises(ValueError):
                        freeze(encode(p))
        for option, value in (("energy_reference", 1e-310), ("temperature", 1e-310), ("alpha", 1e308)):
            with self.subTest(overflow=option):
                p = plan()
                p["model"][option] = value
                p["conditions"][0]["routes"]["escape"]["observable_mismatch"] = 10
                with self.assertRaisesRegex(ValueError, "score exceeds numerical range"):
                    freeze(encode(p))

    def test_complete_cohort_is_required(self):
        for fault in ("missing", "duplicate", "unexpected", "other condition", "different window",
                      "wrong protocol", "unknown outcome", "empty"):
            with self.subTest(fault=fault):
                y = outcomes()
                rows = y["records"]
                if fault == "missing":
                    rows.pop()
                elif fault == "duplicate":
                    rows[-1] = rows[0]
                elif fault == "unexpected":
                    rows[-1]["run_id"] = "z"
                elif fault == "other condition":
                    rows[-1]["condition_id"] = "elsewhere"
                elif fault == "different window":
                    rows[-1]["window"] = "0-500 ps"
                elif fault == "wrong protocol":
                    y["protocol_id"] = "elsewhere"
                elif fault == "unknown outcome":
                    rows[-1]["outcome"] = "merger"
                else:
                    rows.clear()
                with self.assertRaises(ValueError):
                    scored(plan(), y)

    def test_censored_only_cohort_has_no_performance_estimate(self):
        y = outcomes()
        for row in y["records"]:
            row["outcome"] = "censored"
        out = scored(plan(), y)
        self.assertEqual(out["enrolled"], 4)
        self.assertEqual(out["resolved"], 0)
        self.assertIsNone(out["mean_full_minus_barrier_only"])
        self.assertEqual(out["mean_brier"], {"barrier_only": None, "full": None})

    def test_selection_leakage_and_invalid_inputs(self):
        for fault in ("selected", "answer in route", "duplicate enrollment", "empty roster",
                      "duplicate condition", "zero reference", "negative barrier", "NaN", "bad prior", "bool"):
            with self.subTest(fault=fault):
                p = plan()
                c = p["conditions"][0]
                r = c["routes"]["escape"]
                if fault == "selected":
                    p["cohort_design"] = "illustrative_examples"
                elif fault == "answer in route":
                    r["outcome"] = "escape"
                elif fault == "duplicate enrollment":
                    c["run_ids"].append("a")
                elif fault == "empty roster":
                    c["run_ids"] = []
                elif fault == "duplicate condition":
                    p["conditions"].append(copy.deepcopy(c))
                elif fault == "zero reference":
                    p["model"]["energy_reference"] = 0
                elif fault == "negative barrier":
                    r["barrier"] = -1
                elif fault == "NaN":
                    r["barrier"] = float("nan")
                elif fault == "bad prior":
                    r["prior_probability"] = 1.1
                else:
                    r["barrier"] = True
                with self.assertRaises(ValueError):
                    freeze(encode(p))

    def test_prospective_pin_and_input_digests(self):
        p, y = encode(plan()), encode(outcomes())
        raw = freeze(p)
        digest = hashlib.sha256(raw).hexdigest()
        out = evaluate(raw, digest, y)
        self.assertEqual(out["plan_sha256"], hashlib.sha256(p).hexdigest())
        self.assertEqual(out["outcomes_sha256"], hashlib.sha256(y).hexdigest())
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            evaluate(raw + b" ", digest, y)
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            evaluate(raw, digest, b'{"protocol_id":"one","protocol_id":"two"}')

    def test_can_repeat_seed_within_a_different_condition(self):
        p, y = plan(), outcomes()
        b = copy.deepcopy(p["conditions"][0])
        b.update(condition_id="synthetic-B", run_ids=["a"])
        p["conditions"].append(b)
        y["records"].append(dict(y["records"][0], condition_id="synthetic-B"))
        self.assertEqual(scored(p, y)["enrolled"], 5)

    def test_cli_and_exclusive_snapshot_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p, snapshot, y = (root / name for name in ["plan.json", "snapshot.json", "observed.json"])
            p.write_bytes(encode(plan()))
            y.write_bytes(encode(outcomes()))
            with redirect_stdout(StringIO()) as printed:
                main(["freeze", str(p), str(snapshot)])
            digest = printed.getvalue().strip()
            with redirect_stdout(StringIO()) as printed:
                main(["design", str(snapshot), "--snapshot-sha256", digest])
            view = json.loads(printed.getvalue())
            self.assertEqual(view["conditions"]["synthetic-A"]["enrolled"], 4)
            with redirect_stdout(StringIO()) as printed:
                main(["evaluate", str(snapshot), str(y), "--snapshot-sha256", digest])
            self.assertEqual(json.loads(printed.getvalue())["status"], "scored_resolved_events")
            from contextlib import redirect_stderr
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                main(["freeze", str(p), str(snapshot)])
