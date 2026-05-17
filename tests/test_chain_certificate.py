from nagdiff.chain_certificate import (
    all_paths_hit_antichain_at_most_once,
    generate_paths_dag,
    hitting_probability,
    hits_antichain_at_most_once,
    is_antichain,
    validate_submarkov_rows,
)


def test_valid_submarkov_rows():
    t = {"a": {"b": 0.4, "c": 0.6}, "b": {"d": 0.7}, "c": {"d": 0.2}, "d": {}}
    assert validate_submarkov_rows(t)


def test_invalid_submarkov_rows_fail():
    t = {"a": {"b": 0.8, "c": 0.5}}
    assert not validate_submarkov_rows(t)


def test_true_antichain_hit_at_most_once():
    g = {1: [2, 3], 2: [4], 3: [5], 4: [], 5: []}
    anti = {4, 5}
    paths = generate_paths_dag(g, 1)
    assert is_antichain(anti, g)
    assert all_paths_hit_antichain_at_most_once(paths, anti)


def test_non_antichain_can_be_hit_more_than_once():
    path = [1, 2, 3]
    non_anti = {2, 3}
    assert not hits_antichain_at_most_once(path, non_anti)


def test_hitting_probabilities_between_zero_and_one():
    paths = [[1, 2, 4], [1, 3, 5]]
    probs = [0.4, 0.6]
    target = {4}
    hp = hitting_probability(paths, probs, target)
    assert 0.0 <= hp <= 1.0
