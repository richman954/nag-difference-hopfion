import csv
from itertools import permutations
from pathlib import Path

import pytest

from nagdiff.benchmark_controls import DEFAULT_TEMPLATE, STATE, peak_bracket, run_controls


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


@pytest.fixture(scope="module")
def result():
    return run_controls(RAW, ROOT / DEFAULT_TEMPLATE)


def test_template_has_the_same_rank_under_zero_and_all_assignments(result):
    assert result["physical_unit_status"] == "physical_unit_unresolved"
    assert result["validated_absolute_barriers"] == 0
    controls = result["score_controls"]
    rank = [["merger"], ["collapse"], ["escape"]]
    assert controls["zero_barrier_rank"] == rank
    expected_gaps = {
        "conditional_pJ_if_header_scale": 0.062703629465,
        "conditional_pJ_if_SI_density_and_volume": 0.00006274293222,
    }
    assert set(controls["conditional_scenarios"]) == set(expected_gaps)
    for field, scenario in controls["conditional_scenarios"].items():
        assert scenario["barrier_percent_of_gap"] == pytest.approx(expected_gaps[field])
        trials = scenario["permutations"]
        assert len(trials) == scenario["permutations_with_zero_barrier_rank"] == 6
        tuples = [tuple(row["barrier_source_by_scored_path"][name] for name in STATE) for row in trials]
        assert set(tuples) == set(permutations(STATE))
        assert all(row["rank"] == rank for row in trials)
        assert scenario["permutations_with_barrier_only_rank"] == 1
        identity = [trial for trial in trials if trial["publisher_assignment"]]
        assert identity == [trials[tuples.index(tuple(STATE))]]
        assert identity[0]["scores"] == scenario["correct_assignment_scores"]


def test_matched_read_budgets_under_all_independent_phase_pairs(result):
    sampling = result["sampling_controls"]
    assert sampling["full_grid_escape_over_collapse"] == "13483/5264"
    assert sampling["full_grid_images"] == 61
    # Each pair of phases independently selects one offset for each competing exit.
    for stride, budget in ((7, [33, 37]), (8, [34, 40])):
        methods = sampling["by_stride"][str(stride)]
        peak = methods["peak_bracket"]
        blind = methods["longest_gap"]
        assert peak["total_images_read_range"] == blind["total_images_read_range"] == budget
        assert peak["offset_pairs"] == blind["offset_pairs"] == stride**2
        assert peak["both_full_grid_saddles"] == stride**2
        assert blind["both_full_grid_saddles"] == 16

    for method, exact, within_ten_percent, ordered in (
        ("initial", 2, 14, 102),
        ("longest_gap", 32, 60, 113),
        ("peak_bracket", 113, 113, 113),
    ):
        combined = sampling["combined"][method]
        assert combined["offset_pairs"] == combined["resolved_pairs"] == 113
        assert combined["both_full_grid_saddles"] == exact
        assert combined["ratio_within_ten_percent"] == within_ten_percent
        assert combined["escape_above_collapse"] == ordered


def test_publisher_template_two_route_brier_crossover(result):
    scenarios = result["score_controls"]["conditional_scenarios"]
    for convention, expected in (
        ("conditional_pJ_if_header_scale", (0.32931792, 0.49988850, 0.41460321)),
        ("conditional_pJ_if_SI_density_and_volume", (0.32941633, 0.49999989, 0.41470811)),
    ):
        design = scenarios[convention]["two_route_design"]
        assert design["energy_reference_pj"] == design["softmax_temperature"] == 1
        p = design["escape_probability"]
        threshold = design["brier_threshold"]
        assert (p["full"], p["barrier_only"], threshold["escape_fraction_at_tie"]) == pytest.approx(expected)
        assert threshold["full_has_lower_loss_when"] == "below_threshold"
        assert p["prior_only"] == pytest.approx(0.375, abs=1e-12)
        secondary = design["brier_threshold_vs_prior_only"]
        assert secondary["escape_fraction_at_tie"] == pytest.approx((p["full"] + p["prior_only"]) / 2)
        assert secondary["full_has_lower_loss_when"] == "below_threshold"
        for escapes, winner in ((3, "full"), (4, "prior_only"), (5, "barrier_only")):
            losses = {name: escapes * (1 - value)**2 + (10 - escapes) * value**2 for name, value in p.items()}
            assert min(losses, key=losses.get) == winner
            if escapes == 4:
                assert losses["prior_only"] < losses["full"] < losses["barrier_only"]


def test_visible_peak_can_hide_a_higher_peak_in_another_interval():
    curve = [0, 1, 2, 3, 4, 3, 2, 1, 1, 0, 10, 0, -1]
    observed = {i: curve[i] for i in (0, 4, 8, 12)}
    refined = peak_bracket(observed)
    assert refined == set(range(9)) | {12}
    assert max(curve[i] for i in refined) == 4
    assert max(curve) == 10


def test_template_with_zero_coefficients_exposes_permutations_and_ties(tmp_path):
    template = tmp_path / "synthetic_template.csv"
    with template.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("state", "observable_mismatch", "probability", "topology_penalty",
                         "alpha", "beta", "gamma", "delta"))
        # Reversed template rows also exercise matching by state rather than row index.
        for state in reversed(STATE.values()):
            writer.writerow((state, 1, 1, 1, 0, 0, 0, 1e-12))
    controls = run_controls(RAW, template)["score_controls"]
    assert controls["zero_barrier_rank"] == [["collapse", "escape", "merger"]]
    for scenario in controls["conditional_scenarios"].values():
        ranks = {tuple(group[0] for group in trial["rank"]) for trial in scenario["permutations"]}
        assert ranks == set(permutations(STATE))
        assert scenario["permutations_with_zero_barrier_rank"] == 0
        assert scenario["two_route_design"]["brier_threshold"]["tie"] == "every_escape_fraction"
        assert scenario["two_route_design"]["escape_probability"]["prior_only"] == 0.5
