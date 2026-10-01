import math

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
    weights = soft_selection_weights(scores, temperature=1.0)
    assert len(weights) == 3
    assert math.isclose(sum(weights), 1.0)
    # lower score => higher weight
    assert weights[0] > weights[1] > weights[2]


def test_soft_selection_weights_identical():
    scores = [2.0, 2.0, 2.0]
    weights = soft_selection_weights(scores)
    assert len(weights) == 3
    assert all(math.isclose(w, 1.0 / 3.0) for w in weights)


def test_soft_selection_weights_temperature():
    scores = [1.0, 2.0]
    # high temp => more uniform
    weights_high = soft_selection_weights(scores, temperature=100.0)
    assert math.isclose(weights_high[0], weights_high[1], abs_tol=0.05)

    # low temp => winner takes all
    weights_low = soft_selection_weights(scores, temperature=0.01)
    assert weights_low[0] > 0.99
    assert weights_low[1] < 0.01


def test_soft_selection_weights_negative_temperature():
    with pytest.raises(ValueError, match="temperature must be positive"):
        soft_selection_weights([1.0, 2.0], temperature=0.0)
    with pytest.raises(ValueError, match="temperature must be positive"):
        soft_selection_weights([1.0, 2.0], temperature=-1.0)


def test_soft_selection_weights_iterable():
    def score_gen():
        yield 1.0
        yield 2.0
        yield 3.0

    weights_list = soft_selection_weights([1.0, 2.0, 3.0])
    weights_gen = soft_selection_weights(score_gen())

    assert len(weights_gen) == 3
    for w1, w2 in zip(weights_list, weights_gen):
        assert math.isclose(w1, w2)
