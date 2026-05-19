import pytest

from nagdiff.chain_certificate import (
    all_paths_hit_antichain_at_most_once,
    generate_paths,
    hitting_probabilities,
    is_antichain,
    path_hits_subset,
    path_hits_subset_at_most_once,
    row_masses,
    validate_submarkov_kernel,
)


def test_validate_submarkov_kernel_valid_and_row_masses():
    kernel = {"a": {"a": 0.4, "b": 0.5}, "b": {"b": 0.7}}
    assert validate_submarkov_kernel(kernel)
    assert row_masses(kernel) == {"a": 0.9, "b": 0.7}


def test_validate_submarkov_kernel_invalid_row_sum():
    kernel = {"a": {"a": 0.8, "b": 0.4}}
    assert not validate_submarkov_kernel(kernel)


def test_antichain_path_hit_constraints():
    paths = [["1", "2", "4"], ["1", "3", "6"]]
    antichain = {"2", "3"}
    assert path_hits_subset(paths[0], antichain)
    assert all_paths_hit_antichain_at_most_once(paths, antichain)


def test_non_antichain_can_repeat_hits():
    path = ["1", "2", "4", "8"]
    subset = {"2", "4", "8"}
    assert not path_hits_subset_at_most_once(path, subset)


def test_is_antichain_and_empty_singleton_cases():
    order_pairs = {("1", "2"), ("2", "4"), ("1", "4")}
    assert is_antichain(set(), order_pairs)
    assert is_antichain({"2"}, order_pairs)
    assert is_antichain({"2", "3"}, order_pairs)
    assert not is_antichain({"1", "2"}, order_pairs)


def test_hitting_probability_bounded():
    kernel = {"s": {"a": 0.4, "b": 0.6}, "a": {"a": 0.5}, "b": {"b": 0.2}}
    p = hitting_probabilities(kernel, {"s": 1.0}, {"a"}, steps=3)
    assert 0.0 <= p <= 1.0


def test_generate_paths_negative_steps_raises():
    with pytest.raises(ValueError):
        generate_paths({"s": {"s": 1.0}}, "s", -1)
