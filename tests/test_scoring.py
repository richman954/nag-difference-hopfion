from nagdiff.hopfion_terms import SEEDED_BARRIER_DATA, load_barrier_table
from nagdiff.pairwise import pairwise_difference_matrix
from nagdiff.scoring import score_terms, ScoreData, ScoreWeights


def _seed_barriers():
    return {row["state"]: row["barrier_pj"] for row in SEEDED_BARRIER_DATA}


def test_merge_beats_collapse_with_seeded_barriers():
    barriers = _seed_barriers()
    values = [
        barriers["skyrmion_antiskyrmion_merge_to_hopfion"],
        barriers["hopfion_collapse"],
    ]
    data = ScoreData(
        barrier=values,
        observable_mismatch=[0, 0],
        probability=[1, 1],
        topology_penalty=[0, 0],
    )
    weights = ScoreWeights(alpha=0, beta=0, gamma=0)
    scores = score_terms(data, weights)
    d = pairwise_difference_matrix(scores)
    assert d[0][1] < 0


def test_merge_beats_escape_with_seeded_barriers():
    barriers = _seed_barriers()
    values = [
        barriers["skyrmion_antiskyrmion_merge_to_hopfion"],
        barriers["hopfion_escape"],
    ]
    data = ScoreData(
        barrier=values,
        observable_mismatch=[0, 0],
        probability=[1, 1],
        topology_penalty=[0, 0],
    )
    weights = ScoreWeights(alpha=0, beta=0, gamma=0)
    scores = score_terms(data, weights)
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
