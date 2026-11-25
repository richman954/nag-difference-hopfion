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

from nagdiff.route_evaluation import evaluate, freeze, main


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
                main(["evaluate", str(snapshot), str(y), "--snapshot-sha256", digest])
            self.assertEqual(json.loads(printed.getvalue())["status"], "scored_resolved_events")
            from contextlib import redirect_stderr
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                main(["freeze", str(p), str(snapshot)])
