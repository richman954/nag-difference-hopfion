from nagdiff.hopfion_terms import SEEDED_BARRIER_DATA, load_barrier_table
import pytest

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


def test_soft_selection_weights_temperature_error():
    with pytest.raises(ValueError, match="temperature must be positive"):
        soft_selection_weights([1.0, 2.0], temperature=0.0)

    with pytest.raises(ValueError, match="temperature must be positive"):
        soft_selection_weights([1.0, 2.0], temperature=-1.0)


def test_soft_selection_weights():
    # Lower score => higher weight. Check that order is correct.
    weights = soft_selection_weights([1.0, 2.0], temperature=1.0)
    assert len(weights) == 2
    assert sum(weights) == pytest.approx(1.0)
    assert weights[0] > weights[1]

    # Test with different temperature
    weights_hot = soft_selection_weights([1.0, 2.0], temperature=10.0)
    assert len(weights_hot) == 2
    assert sum(weights_hot) == pytest.approx(1.0)
    assert weights_hot[0] > weights_hot[1]

    # Weight diff should be smaller for hotter temp
    diff_normal = weights[0] - weights[1]
    diff_hot = weights_hot[0] - weights_hot[1]
    assert diff_hot < diff_normal
