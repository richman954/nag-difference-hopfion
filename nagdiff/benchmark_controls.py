"""Scoring and subsampling controls on the three published Chen et al. energy paths."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from fractions import Fraction
from itertools import permutations, product
import json
import math
from pathlib import Path

from .chen2026_audit import AuditError, audit_publisher_pair
from .route_evaluation import brier_threshold, prior_only_escape_probability
from .scoring import score_terms, soft_selection_weights


STATE = {
    "merger": "skyrmion_antiskyrmion_merge_to_hopfion",
    "collapse": "hopfion_collapse",
    "escape": "hopfion_escape",
}
AUXILIARIES = ("observable_mismatch", "probability", "topology_penalty")
COEFFICIENTS = ("alpha", "beta", "gamma", "delta")
DEFAULT_TEMPLATE = Path("data/processed/nag_hopfion_scoring_template.csv")


def _template_inputs(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        required = {"state", *AUXILIARIES, *COEFFICIENTS}
        if len(headers) != len(set(headers)) or not required.issubset(headers):
            raise ValueError("Scoring template has missing or duplicate column headers")
        rows = list(reader)
    by_state = {row["state"]: row for row in rows}
    if len(rows) != len(STATE) or set(by_state) != set(STATE.values()):
        raise ValueError("Expected one scoring-template row for each of the three target states")
    values = {}
    for key in (*AUXILIARIES, *COEFFICIENTS):
        try:
            values[key] = [float(by_state[state][key]) for state in STATE.values()]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric template cell in {key}") from exc
        if not all(map(math.isfinite, values[key])):
            raise ValueError(f"Nonfinite template value in {key}")
    if any(len(set(values[key])) != 1 for key in COEFFICIENTS):
        raise ValueError("The scorer requires one common set of coefficients across all rows")
    coeffs = {key: values[key][0] for key in COEFFICIENTS}
    for p in values["probability"]:
        if not 0 <= p <= 1 or p + coeffs["delta"] <= 0:
            raise ValueError("Invalid probability or undefined log-probability term")
    return [values[key] for key in AUXILIARIES], coeffs


def _rank(scores):
    """Lower scores rank first. Group exact ties so row order cannot break them."""
    return [sorted(name for name, value in scores.items() if value == level)
            for level in sorted(set(scores.values()))]


def _scoring_controls(paths, template):
    aux, coeffs = _template_inputs(template)

    def evaluate(barriers):
        scores = score_terms(barriers, *aux, **coeffs)
        if not all(map(math.isfinite, scores)):
            raise ValueError("Scoring template produces nonfinite scores")
        return dict(zip(STATE, scores))

    zero = evaluate([0.0] * len(STATE))
    zero_rank = _rank(zero)
    exits = ("collapse", "escape")
    route_priors = dict(zip(STATE, aux[AUXILIARIES.index("probability")]))
    prior_p = prior_only_escape_probability(
        [route_priors[path] for path in exits],
        beta=coeffs["beta"], delta=coeffs["delta"], temperature=1.0,
    )
    scenarios = {}
    for field in ("conditional_pJ_if_header_scale", "conditional_pJ_if_SI_density_and_volume"):
        barriers = {name: float(paths[name][field]) for name in STATE}
        full = evaluate(barriers.values())
        gap = full["escape"] - full["collapse"]
        barrier_gap = barriers["escape"] - barriers["collapse"]
        # These settings reproduce the template's numeric pJ coefficient.
        # Merger starts in another basin and is excluded from the two-route forecast.
        full_p = soft_selection_weights([full[path] for path in exits], 1.0)[1]
        barrier_p = soft_selection_weights([barriers[path] for path in exits], 1.0)[1]
        trials = []
        for perm in permutations(STATE):
            assigned = dict(zip(STATE, perm))
            assigned_barriers = {name: barriers[source] for name, source in assigned.items()}
            scores = evaluate(assigned_barriers.values())
            trials.append({
                "barrier_source_by_scored_path": assigned,
                "publisher_assignment": all(name == source for name, source in assigned.items()),
                "scores": scores,
                "rank": _rank(scores),
                "barrier_only_rank": _rank(assigned_barriers),
            })
        scenarios[field] = {
            "barriers": barriers, "correct_assignment_scores": full,
            "escape_minus_collapse_gap": gap,
            "barrier_percent_of_gap": 100 * barrier_gap / gap if gap else None,
            "two_route_design": {
                "energy_reference_pj": 1.0, "softmax_temperature": 1.0,
                "escape_probability": {"full": full_p, "barrier_only": barrier_p, "prior_only": prior_p},
                "brier_threshold": brier_threshold(full_p, barrier_p),
                "brier_threshold_vs_prior_only": brier_threshold(full_p, prior_p),
            },
            "permutations": trials,
            "permutations_with_zero_barrier_rank": sum(row["rank"] == zero_rank for row in trials),
            "permutations_with_barrier_only_rank": sum(row["rank"] == row["barrier_only_rank"] for row in trials),
        }
    return {"coefficients": coeffs, "zero_barrier_scores": zero, "zero_barrier_rank": zero_rank,
            "conditional_scenarios": scenarios}


def peak_bracket(observed):
    """Return IDs after filling both intervals neighboring the highest visible local peak."""
    ids = sorted(observed)
    peaks = [mid for left, mid, right in zip(ids, ids[1:], ids[2:])
             if observed[mid] > max(observed[left], observed[right])]
    # ids and peaks are ascending, so an equal maximum selects the earlier image.
    target = max(peaks or ids, key=observed.__getitem__)
    pos = ids.index(target)
    left = ids[max(0, pos - 1)]
    right = ids[min(pos + 1, len(ids) - 1)]
    return set(ids).union(range(left, right + 1))


def _fill_longest_gaps(initial, extra_reads):
    """Fill the earliest longest gap, rounding its midpoint down."""
    ids = set(initial)
    for _ in range(extra_reads):
        ordered = sorted(ids)
        left, right = max(zip(ordered, ordered[1:]), key=lambda pair: pair[1] - pair[0])
        ids.add((left + right) // 2)
    return ids


@dataclass(frozen=True)
class Reading:
    rise: Fraction
    resolved: bool
    exact: bool
    count: int


def _read(curve, ids, reference_peak):
    top = max(curve[i] for i in ids)
    peaks = [i for i in ids if curve[i] == top]
    resolved = len(peaks) == 1 and peaks[0] not in (0, len(curve) - 1) and top > curve[0]
    return Reading(top - curve[0], resolved, resolved and peaks[0] == reference_peak, len(ids))


def _phase_readings(curve, stride):
    reference_peak = curve.index(max(curve))
    phases = {"initial": [], "peak_bracket": [], "longest_gap": []}
    for offset in range(stride):
        base = {0, len(curve) - 1, *range(offset, len(curve), stride)}
        refined = peak_bracket({i: curve[i] for i in base})
        blind = _fill_longest_gaps(base, len(refined) - len(base))
        for name, ids in (("initial", base), ("peak_bracket", refined), ("longest_gap", blind)):
            phases[name].append(_read(curve, ids, reference_peak))
    return phases


def _summarize(pairs, reference):
    resolved = [(c, e) for c, e in pairs if c.resolved and e.resolved]
    ratios = [e.rise / c.rise for c, e in resolved]
    cost = [c.count + e.count for c, e in pairs]
    return {"offset_pairs": len(pairs), "resolved_pairs": len(resolved),
            "escape_above_collapse": sum(r > 1 for r in ratios),
            "both_full_grid_saddles": sum(c.exact and e.exact for c, e in resolved),
            "ratio_within_ten_percent": sum(abs(r / reference - 1) <= Fraction(1, 10) for r in ratios),
            "total_images_read_range": [min(cost), max(cost)]}


def _sampling_controls(paths):
    c, e = (list(map(Fraction, paths[name]["density_profile"])) for name in ("collapse", "escape"))
    reference = (max(e) - e[0]) / (max(c) - c[0])
    all_pairs = {}
    by_stride = {}
    for stride in (7, 8):
        collapse, escape = _phase_readings(c, stride), _phase_readings(e, stride)
        by_stride[str(stride)] = {}
        for method in collapse:
            pairs = list(product(collapse[method], escape[method]))
            by_stride[str(stride)][method] = _summarize(pairs, reference)
            all_pairs.setdefault(method, []).extend(pairs)
    return {"full_grid_escape_over_collapse": str(reference), "full_grid_images": len(c) + len(e),
            "by_stride": by_stride, "combined": {
                method: _summarize(pairs, reference) for method, pairs in all_pairs.items()}}


def run_controls(raw_dir="data/raw", template=DEFAULT_TEMPLATE):
    """Replay template perturbations and matched-budget retrospective refinement."""
    audit = audit_publisher_pair(Path(raw_dir), include_profiles=True)
    paths = {branch["path"]: branch for branch in audit["paths"]}
    return {
        "doi": audit["doi"], "source_workbooks": audit["sources"], "scoring_template": str(template),
        "physical_unit_status": audit["status"], "validated_absolute_barriers": audit["validated_count"],
        "score_controls": _scoring_controls(paths, template), "sampling_controls": _sampling_controls(paths),
        "scope": "Permutations are synthetic assignments. Offsets reuse two published discrete paths. "
                 "No route-labeled held-out trajectories are scored by this control.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    args = parser.parse_args(argv)
    try:
        result = run_controls(args.raw, args.template)
    except (AuditError, ValueError, OSError) as exc:
        parser.exit(2, f"Benchmark controls failed: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
