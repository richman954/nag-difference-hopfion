"""Freeze prospective two-route predictions, then evaluate a complete held-out cohort.

The event label is escape (1) or collapse (0) from an initial hopfion. A shared
energy reference nondimensionalizes both barriers. Both models use the same
softmax temperature. Censored and indeterminate runs count toward coverage.
The paired binary Brier difference is full minus barrier-only (lower is better).
Barriers must be nonnegative and route priors must lie in [0,1]. The shared
energy reference, temperature, and log offset must be positive. The upstream
scorer accepts finite signed auxiliary features and their coefficients.

Preserve the printed snapshot digest independently before unblinding outcomes.
A matching digest verifies bytes. The registry, split, timing, feature
independence, and completeness of the declared cohort require external evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from .barrier_workbooks import normalize_to_pj
from .scoring import score_terms, soft_selection_weights


ROUTES = ("collapse", "escape")
OUTCOMES = (*ROUTES, "censored", "indeterminate")
SCORES = ("barrier_only", "full")


def _keys(value, names):
    if not isinstance(value, dict) or set(value) != set(names.split()):
        raise ValueError(f"expected exactly these fields: {names}")
    return value


def _text(value):
    if not isinstance(value, str) or not value.strip() or value.strip() != value:
        raise ValueError("expected a nonempty string with no leading or trailing whitespace")
    return value


def _number(value):
    if type(value) not in (int, float):
        raise ValueError("expected a finite number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError("expected a finite number representable as a float") from exc
    if not math.isfinite(number):
        raise ValueError("expected a finite number")
    return number


def _list(value):
    if not isinstance(value, list) or not value:
        raise ValueError("expected a nonempty list")
    return value


def _decode(raw):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"duplicate JSON key: {key}")
            obj[key] = value
        return obj
    return json.loads(raw, object_pairs_hook=unique)


def _encoded(obj):
    return (json.dumps(obj, allow_nan=False, indent=2, sort_keys=True) + "\n").encode()


def _probabilities(routes, config):
    _keys(routes, "collapse escape")
    fields = ["barrier", "observable_mismatch", "prior_probability", "topology_penalty"]
    inputs = []
    for route in ROUTES:
        entry = _keys(routes[route], " ".join(fields))
        row = [_number(entry[f]) for f in fields]
        if row[0] < 0 or not 0 <= row[2] <= 1:
            raise ValueError("negative barrier or route prior outside [0,1]")
        inputs.append(row)
    b, mismatch, prior, topology = zip(*inputs)
    b = [v / config["energy_reference"] for v in b]
    full = score_terms(b, mismatch, prior, topology, alpha=config["alpha"],
                       beta=config["beta"], gamma=config["gamma"], delta=config["delta"])
    probs = {}
    for name, scores in zip(SCORES, (b, full)):
        temperature = config["temperature"]
        if not all(math.isfinite(s / temperature) for s in scores):
            raise ValueError("score exceeds numerical range at the specified temperature")
        probs[name] = soft_selection_weights(scores, temperature)[1]
    return probs


def freeze(plan_bytes: bytes) -> bytes:
    """Return canonical snapshot bytes, including exact input SHA-256 and run roster."""
    plan = _keys(_decode(plan_bytes),
                 "protocol_id cohort_design enrollment_source feature_source model conditions")
    if plan["cohort_design"] != "all_enrolled":
        raise ValueError("the held-out cohort must include all enrolled runs")
    for f in ("protocol_id", "enrollment_source", "feature_source"):
        _text(plan[f])
    config = _keys(plan["model"], "energy_unit energy_reference alpha beta gamma delta temperature")
    # The common unit cancels in the barrier/reference ratio after validating it.
    normalize_to_pj(1, config["energy_unit"])
    for f in ("energy_reference", "alpha", "beta", "gamma", "delta", "temperature"):
        _number(config[f])
    if min(config[f] for f in ("energy_reference", "delta", "temperature")) <= 0:
        raise ValueError("energy_reference, delta, and temperature must be positive")
    predictions = {}
    for entry in _list(plan["conditions"]):
        _keys(entry, "condition_id window run_ids routes")
        condition = _text(entry["condition_id"])
        runs = [_text(run) for run in _list(entry["run_ids"])]
        if condition in predictions or len(set(runs)) != len(runs):
            raise ValueError("duplicate condition or duplicate enrolled run within a condition")
        predictions[condition] = {
            "window": _text(entry["window"]), "run_ids": runs,
            "escape_probability": _probabilities(entry["routes"], config),
        }
    return _encoded({
        "schema_version": 1, "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "protocol_id": plan["protocol_id"], "cohort_design": plan["cohort_design"],
        "enrollment_source": plan["enrollment_source"], "feature_source": plan["feature_source"],
        "model": config, "conditions": predictions,
    })


def evaluate(snapshot_bytes: bytes, expected_sha256: str, outcome_bytes: bytes) -> dict:
    """Require the pre-recorded digest and exactly one outcome for every enrolled run."""
    received = hashlib.sha256(snapshot_bytes).hexdigest()
    if received != expected_sha256:
        raise ValueError("snapshot differs from supplied SHA-256")
    snap = _keys(_decode(snapshot_bytes), "schema_version plan_sha256 protocol_id cohort_design "
                 "enrollment_source feature_source model conditions")
    if snap["schema_version"] != 1 or snap["cohort_design"] != "all_enrolled":
        raise ValueError("unsupported snapshot or selected cohort")
    data = _keys(_decode(outcome_bytes), "protocol_id outcome_source records")
    if data["protocol_id"] != snap["protocol_id"]:
        raise ValueError("outcomes have a different protocol_id")
    _text(data["outcome_source"])
    conditions = snap["conditions"]
    if not isinstance(conditions, dict) or not conditions:
        raise ValueError("expected a snapshot with enrolled conditions")
    roster = set()
    for condition, entry in conditions.items():
        _text(condition)
        _keys(entry, "window run_ids escape_probability")
        _text(entry["window"])
        probs = _keys(entry["escape_probability"], "barrier_only full")
        if not all(0 <= _number(v) <= 1 for v in probs.values()):
            raise ValueError("snapshot probability outside [0,1]")
        runs = [_text(run) for run in _list(entry["run_ids"])]
        if len(set(runs)) != len(runs):
            raise ValueError("duplicate enrollment")
        roster.update((condition, run) for run in runs)

    seen = set()
    counts = Counter({state: 0 for state in OUTCOMES})
    paired = []
    for record in _list(data["records"]):
        _keys(record, "condition_id run_id window outcome")
        key = (_text(record["condition_id"]), _text(record["run_id"]))
        if key not in roster or key in seen:
            raise ValueError(f"duplicate or unenrolled outcome: {key!r}")
        seen.add(key)
        entry = conditions[key[0]]
        if entry["window"] != record["window"]:
            raise ValueError(f"observation window mismatch: {key!r}")
        outcome = record["outcome"]
        if outcome not in OUTCOMES:
            raise ValueError(f"unknown outcome: {outcome!r}")
        counts[outcome] += 1
        if outcome in ROUTES:
            y = int(outcome == "escape")
            losses = {m: (p - y) ** 2 for m, p in entry["escape_probability"].items()}
            paired.append({"condition_id": key[0], "run_id": key[1], "outcome": outcome,
                           "brier": losses, "full_minus_barrier_only": losses["full"] - losses["barrier_only"]})
    if seen != roster:
        raise ValueError(f"missing outcomes for {len(roster - seen)} enrolled run(s)")
    n = len(paired)
    means = {m: math.fsum(p["brier"][m] for p in paired) / n if n else None for m in SCORES}
    return {
        "status": "scored_resolved_events" if n else "no_resolved_events",
        "estimand": "Mean paired binary Brier loss conditional on observing a resolved route in the planned window.",
        "snapshot_sha256": received, "plan_sha256": snap["plan_sha256"],
        "outcomes_sha256": hashlib.sha256(outcome_bytes).hexdigest(), "outcome_source": data["outcome_source"],
        "enrolled": len(roster), "outcome_counts": dict(counts), "resolved": n, "resolved_fraction": n / len(roster),
        "mean_brier": means, "mean_full_minus_barrier_only": (
            math.fsum(p["full_minus_barrier_only"] for p in paired) / n if n else None),
        "paired_runs": paired,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    lock = commands.add_parser("freeze", help="create predictions before unblinding")
    lock.add_argument("plan", type=Path)
    lock.add_argument("snapshot", type=Path)
    test = commands.add_parser("evaluate", help="score the complete outcome roster")
    test.add_argument("snapshot", type=Path)
    test.add_argument("outcomes", type=Path)
    test.add_argument("--snapshot-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            raw = freeze(args.plan.read_bytes())
            # Publish a complete file; link creation also rejects an existing destination.
            with TemporaryDirectory(dir=args.snapshot.parent) as tmp:
                candidate = Path(tmp) / "snapshot.json"
                candidate.write_bytes(raw)
                os.link(candidate, args.snapshot)
            print(hashlib.sha256(raw).hexdigest())
        else:
            result = evaluate(args.snapshot.read_bytes(), args.snapshot_sha256, args.outcomes.read_bytes())
            print(_encoded(result).decode(), end="")
    except (ValueError, OverflowError, OSError) as exc:
        parser.exit(2, f"route evaluation: {exc}\n")


if __name__ == "__main__":
    main()
