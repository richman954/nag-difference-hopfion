"""Freeze prospective two-route predictions, then evaluate a complete held-out cohort.

The event label is escape (1) or collapse (0) from an initial hopfion. A shared
energy reference nondimensionalizes both barriers. All forecasts use the same
softmax temperature. Censored and indeterminate runs count toward coverage.
The primary paired binary Brier difference is full minus barrier-only (lower
is better). Version 2 snapshots also freeze a descriptive prior-only comparison.
It retains only the full model's beta-weighted log-prior with the same offset.
At beta zero, prior-only assigns equal weight to both exits. Original version 1
snapshots retain their two forecasts.
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
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .barrier_workbooks import normalize_to_pj
from .scoring import score_terms, soft_selection_weights


ROUTES = ("collapse", "escape")
OUTCOMES = (*ROUTES, "censored", "indeterminate")
SCORES = ("barrier_only", "full")  # Model names in the original two-forecast API.
MODELS_BY_VERSION = {1: SCORES, 2: ("barrier_only", "prior_only", "full")}


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


def _probability(value):
    p = _number(value)
    if not 0 <= p <= 1:
        raise ValueError("probability outside [0,1]")
    return p


def brier_threshold(full_probability: float, barrier_probability: float) -> dict:
    """Compare the forecasts at any escape fraction q among resolved runs.

    The mean full-minus-baseline Brier loss is (f-b)(f+b-2q).
    The exact fraction preserves ties at midpoints between adjacent floats.
    """
    full = _probability(full_probability)
    barrier = _probability(barrier_probability)
    if full == barrier:
        return {"escape_fraction_at_tie": None, "escape_fraction_at_tie_exact": None,
                "full_has_lower_loss_when": "never", "tie": "every_escape_fraction"}
    midpoint = (Fraction(full) + Fraction(barrier)) / 2
    return {"escape_fraction_at_tie": float(midpoint), "escape_fraction_at_tie_exact": str(midpoint),
            "full_has_lower_loss_when": "above_threshold" if full > barrier else "below_threshold",
            "tie": "at_threshold"}


def _escape_probability(scores, temperature):
    if not all(math.isfinite(s / temperature) for s in scores):
        raise ValueError("score exceeds numerical range at the specified temperature")
    return soft_selection_weights(scores, temperature)[1]


def prior_only_escape_probability(priors, *, beta, delta, temperature):
    """Forecast escape using just the log-prior term, with priors in collapse, escape order."""
    try:
        collapse, escape = priors
    except (TypeError, ValueError) as exc:
        raise ValueError("expected one prior per route in collapse, escape order") from exc
    prior = [_probability(collapse), _probability(escape)]
    beta, delta, temperature = _number(beta), _number(delta), _number(temperature)
    # Historical scoring templates allow a zero log offset for positive priors.
    # Prospective plans additionally enforce a positive offset during validation.
    if temperature <= 0 or any(p + delta <= 0 for p in prior):
        raise ValueError("temperature and shifted priors must be positive")
    zeros = [0.0] * len(ROUTES)
    scores = score_terms(zeros, zeros, prior, zeros, beta=beta, delta=delta)
    return _escape_probability(scores, temperature)


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
    temperature = config["temperature"]
    return {
        "barrier_only": _escape_probability(b, temperature),
        "full": _escape_probability(full, temperature),
        "prior_only": prior_only_escape_probability(prior, beta=config["beta"],
                                                   delta=config["delta"], temperature=temperature),
    }


def _validate_protocol(obj):
    if obj["cohort_design"] != "all_enrolled":
        raise ValueError("the held-out cohort must include all enrolled runs")
    for f in ("protocol_id", "enrollment_source", "feature_source"):
        _text(obj[f])
    config = _keys(obj["model"], "energy_unit energy_reference alpha beta gamma delta temperature")
    # The common unit cancels in the barrier/reference ratio after validating it.
    normalize_to_pj(1, config["energy_unit"])
    for f in ("energy_reference", "alpha", "beta", "gamma", "delta", "temperature"):
        _number(config[f])
    if min(config[f] for f in ("energy_reference", "delta", "temperature")) <= 0:
        raise ValueError("energy_reference, delta, and temperature must be positive")


def freeze(plan_bytes: bytes) -> bytes:
    """Return canonical snapshot bytes, including exact input SHA-256 and run roster."""
    plan = _keys(_decode(plan_bytes),
                 "protocol_id cohort_design enrollment_source feature_source model conditions")
    _validate_protocol(plan)
    config = plan["model"]
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
        "schema_version": 2, "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "protocol_id": plan["protocol_id"], "cohort_design": plan["cohort_design"],
        "enrollment_source": plan["enrollment_source"], "feature_source": plan["feature_source"],
        "model": config, "conditions": predictions,
    })


def _read_snapshot(snapshot_bytes, expected_sha256):
    if hashlib.sha256(snapshot_bytes).hexdigest() != expected_sha256:
        raise ValueError("snapshot differs from supplied SHA-256")
    snap = _keys(_decode(snapshot_bytes), "schema_version plan_sha256 protocol_id cohort_design "
                 "enrollment_source feature_source model conditions")
    version = snap["schema_version"]
    if type(version) is not int or version not in MODELS_BY_VERSION:
        raise ValueError("unsupported snapshot schema version")
    if not re.fullmatch(r"[0-9a-f]{64}", _text(snap["plan_sha256"])):
        raise ValueError("invalid plan SHA-256 in snapshot")
    _validate_protocol(snap)
    conditions = snap["conditions"]
    if not isinstance(conditions, dict) or not conditions:
        raise ValueError("expected a snapshot with enrolled conditions")
    for condition, entry in conditions.items():
        _text(condition)
        _keys(entry, "window run_ids escape_probability")
        _text(entry["window"])
        probs = _keys(entry["escape_probability"], " ".join(MODELS_BY_VERSION[version]))
        for p in probs.values():
            _probability(p)
        runs = [_text(run) for run in _list(entry["run_ids"])]
        if len(set(runs)) != len(runs):
            raise ValueError("duplicate enrollment")
    return snap


def _condition_design(entry):
    probs = entry["escape_probability"]
    result = {"window": entry["window"], "enrolled": len(entry["run_ids"]),
              "escape_probability": probs, "brier_threshold": brier_threshold(probs["full"], probs["barrier_only"])}
    if "prior_only" in probs:
        result["brier_threshold_vs_prior_only"] = brier_threshold(probs["full"], probs["prior_only"])
    return result


def design(snapshot_bytes: bytes, expected_sha256: str) -> dict:
    """Describe the conditions in which either frozen forecast would score better, before outcomes."""
    snap = _read_snapshot(snapshot_bytes, expected_sha256)
    return {"protocol_id": snap["protocol_id"], "snapshot_sha256": expected_sha256,
            "plan_sha256": snap["plan_sha256"],
            "conditions": {condition: _condition_design(entry) for condition, entry in snap["conditions"].items()}}


def _mean_losses(paired, models):
    n = len(paired)
    result = {"mean_brier": {m: math.fsum(p["brier"][m] for p in paired) / n if n else None for m in models}}
    for baseline in models:
        if baseline != "full":
            key = f"full_minus_{baseline}"
            result[f"mean_{key}"] = math.fsum(p[key] for p in paired) / n if n else None
    return result


def evaluate(snapshot_bytes: bytes, expected_sha256: str, outcome_bytes: bytes) -> dict:
    """Require the pre-recorded digest and exactly one outcome for every enrolled run."""
    snap = _read_snapshot(snapshot_bytes, expected_sha256)
    data = _keys(_decode(outcome_bytes), "protocol_id outcome_source records")
    if data["protocol_id"] != snap["protocol_id"]:
        raise ValueError("outcomes have a different protocol_id")
    _text(data["outcome_source"])
    conditions = snap["conditions"]
    models = MODELS_BY_VERSION[snap["schema_version"]]
    baselines = [name for name in models if name != "full"]
    roster = {(condition, run) for condition, entry in conditions.items() for run in entry["run_ids"]}
    seen = set()
    counts_by_condition = {condition: Counter(dict.fromkeys(OUTCOMES, 0)) for condition in conditions}
    paired_by_condition = {condition: [] for condition in conditions}
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
        counts_by_condition[key[0]][outcome] += 1
        if outcome in ROUTES:
            y = int(outcome == "escape")
            losses = {m: (p - y) ** 2 for m, p in entry["escape_probability"].items()}
            differences = {f"full_minus_{b}": losses["full"] - losses[b] for b in baselines}
            paired.append({"condition_id": key[0], "run_id": key[1], "outcome": outcome,
                           "brier": losses, **differences})
            paired_by_condition[key[0]].append(paired[-1])
    if seen != roster:
        raise ValueError(f"missing outcomes for {len(roster - seen)} enrolled run(s)")
    n = len(paired)
    counts = {outcome: sum(c[outcome] for c in counts_by_condition.values()) for outcome in OUTCOMES}
    summaries = {}
    for condition, entry in conditions.items():
        rows = paired_by_condition[condition]
        totals = counts_by_condition[condition]
        summaries[condition] = {
            **_condition_design(entry), "outcome_counts": dict(totals),
            "resolved": len(rows), "resolved_fraction": len(rows) / len(entry["run_ids"]),
            "observed_escape_fraction": totals["escape"] / len(rows) if rows else None,
            **_mean_losses(rows, models),
        }
    k = len(conditions)
    missing = sorted(c for c in conditions if not paired_by_condition[c])
    equal = {
        "conditions": k, "conditions_without_resolved_events": missing,
        "mean_brier": {m: None if missing else math.fsum(s["mean_brier"][m] for s in summaries.values()) / k
                       for m in models},
    }
    for baseline in baselines:
        key = f"mean_full_minus_{baseline}"
        equal[key] = None if missing else math.fsum(s[key] for s in summaries.values()) / k
    return {
        "status": "scored_resolved_events" if n else "no_resolved_events",
        "estimand": "Mean paired binary Brier loss conditional on observing a resolved route in the planned window.",
        "snapshot_sha256": expected_sha256, "plan_sha256": snap["plan_sha256"],
        "outcomes_sha256": hashlib.sha256(outcome_bytes).hexdigest(), "outcome_source": data["outcome_source"],
        "enrolled": len(roster), "outcome_counts": dict(counts), "resolved": n, "resolved_fraction": n / len(roster),
        **_mean_losses(paired, models), "by_condition": summaries, "equal_condition": equal,
        "paired_runs": paired,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    lock = commands.add_parser("freeze", help="create predictions before unblinding")
    lock.add_argument("plan", type=Path)
    lock.add_argument("snapshot", type=Path)
    inspect = commands.add_parser("design", help="show outcome-blind Brier thresholds by condition")
    inspect.add_argument("snapshot", type=Path)
    inspect.add_argument("--snapshot-sha256", required=True)
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
        elif args.command == "design":
            print(_encoded(design(args.snapshot.read_bytes(), args.snapshot_sha256)).decode(), end="")
        else:
            result = evaluate(args.snapshot.read_bytes(), args.snapshot_sha256, args.outcomes.read_bytes())
            print(_encoded(result).decode(), end="")
    except (ValueError, OverflowError, OSError) as exc:
        parser.exit(2, f"route evaluation: {exc}\n")


if __name__ == "__main__":
    main()
