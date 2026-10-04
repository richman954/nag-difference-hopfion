import pytest

from nagdiff.hopfion_terms import SEEDED_BARRIER_DATA, load_barrier_table
from nagdiff.pairwise import pairwise_difference_matrix
from nagdiff.scoring import score_terms, soft_selection_weights


def _seed_barriers():
    return {row["state"]: row["barrier_pj"] for row in SEEDED_BARRIER_DATA}


def test_merge_beats_collapse_with_seeded_barriers():
    barriers = _seed_barriers()
    values = [
        barriers["skyrmion_antiskyrmion_merge_to_hopfion"],
        barriers["hopfion_collapse"],
    ]
    scores = score_terms(values, [0, 0], [1, 1], [0, 0], alpha=0, beta=0, gamma=0)
    d = pairwise_difference_matrix(scores)
    assert d[0][1] < 0


def test_merge_beats_escape_with_seeded_barriers():
    barriers = _seed_barriers()
    values = [
        barriers["skyrmion_antiskyrmion_merge_to_hopfion"],
        barriers["hopfion_escape"],
    ]
    scores = score_terms(values, [0, 0], [1, 1], [0, 0], alpha=0, beta=0, gamma=0)
    d = pairwise_difference_matrix(scores)
    assert d[0][1] < 0


def test_load_barrier_table_fallback_mode(tmp_path):
    out = load_barrier_table(raw_dir=tmp_path)
    assert out["mode"] == "fallback"
    assert out["extracted_count"] == 0
    assert len(out["seeded_records"]) == 3


def test_load_barrier_table_extracted_mode(tmp_path):
    f13 = tmp_path / "MOESM13.csv"
    f16 = tmp_path / "MOESM16.csv"
    f13.write_text(
        "label,value\n"
        "skyrmion antiskyrmion merge hopfion barrier,2.24e-4\n"
        "hopfion collapse barrier,2.86e-4\n",
        encoding="utf-8",
    )
    f16.write_text(
        "label,value\n"
        "hopfion escape barrier,7.32e-4\n",
        encoding="utf-8",
    )

    out = load_barrier_table(raw_dir=tmp_path)
    assert out["mode"] == "extracted"
    assert out["extracted_count"] == 3
    recs = {r["state"]: r for r in out["records"]}
    assert recs["skyrmion_antiskyrmion_merge_to_hopfion"]["provenance_status"] == "extracted_from_raw_moesm"


def test_soft_selection_weights_basic():
    scores = [1.0, 2.0, 3.0]
    weights = soft_selection_weights(scores)

    # Lower score should have higher weight
    assert weights[0] > weights[1]
    assert weights[1] > weights[2]

    # Sum of weights should be approximately 1.0
    assert pytest.approx(sum(weights)) == 1.0


def test_soft_selection_weights_temperature():
    scores = [1.0, 5.0]

    # Base temperature
    weights_base = soft_selection_weights(scores, temperature=1.0)

    # Low temperature should make the difference more pronounced
    weights_low_temp = soft_selection_weights(scores, temperature=0.1)

    # High temperature should smooth out the differences
    weights_high_temp = soft_selection_weights(scores, temperature=10.0)

    # Compare disparity (difference between highest and lowest weight)
    disparity_base = weights_base[0] - weights_base[1]
    disparity_low = weights_low_temp[0] - weights_low_temp[1]
    disparity_high = weights_high_temp[0] - weights_high_temp[1]

    assert disparity_low > disparity_base
    assert disparity_base > disparity_high

    # For high temperature, weights should be closer to uniform (0.5 each)
    assert pytest.approx(weights_high_temp[0], abs=0.1) == 0.5
    assert pytest.approx(weights_high_temp[1], abs=0.1) == 0.5


def test_soft_selection_weights_invalid_temperature():
    scores = [1.0, 2.0]

    with pytest.raises(ValueError, match="temperature must be positive"):
        soft_selection_weights(scores, temperature=0.0)

    with pytest.raises(ValueError, match="temperature must be positive"):
        soft_selection_weights(scores, temperature=-1.0)


def test_soft_selection_weights_empty():
    # Calling with empty list should raise ValueError from built-in max()
    with pytest.raises(ValueError):
        soft_selection_weights([])
