from nagdiff.chain_certificate import (
    all_paths_hit_antichain_at_most_once,
    generate_paths,
    hitting_probabilities,
    is_antichain,
    path_hits_subset_at_most_once,
    row_masses,
    validate_submarkov_kernel,
)


def _reachable(graph, src, dst):
    if src == dst:
        return True
    stack = [src]
    seen = set()
    while stack:
        u = stack.pop()
        for v in graph.get(u, []):
            if v == dst:
                return True
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return False


def test_valid_submarkov_rows_pass() -> None:
    kernel = {"a": {"b": 0.4, "c": 0.3}, "b": {"d": 0.5}, "c": {"d": 0.2}, "d": {}}
    assert validate_submarkov_kernel(kernel)
    masses = row_masses(kernel)
    assert masses["a"] <= 1.0


def test_row_mass_over_one_fails() -> None:
    kernel = {"a": {"b": 0.7, "c": 0.5}}
    assert not validate_submarkov_kernel(kernel)


def test_hitting_probabilities_are_bounded() -> None:
    kernel = {"a": {"b": 0.5, "c": 0.25}, "b": {"d": 0.5}, "c": {"d": 0.25}, "d": {}}
    probs = hitting_probabilities(kernel, {"a": 1.0}, max_steps=20)
    assert probs
    assert all(0.0 <= p <= 1.0 for p in probs.values())


def test_valid_antichain_hit_at_most_once_on_paths() -> None:
    graph = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}
    antichain = {"b", "c"}
    order = lambda x, y: _reachable(graph, x, y) and x != y
    assert is_antichain(antichain, order)
    paths = generate_paths(graph, "a")
    assert all_paths_hit_antichain_at_most_once(paths, antichain)


def test_non_antichain_can_be_hit_more_than_once() -> None:
    path = [1, 2, 3]
    subset = {2, 3}
    assert not path_hits_subset_at_most_once(path, subset)


def test_empty_and_singleton_antichain_are_valid() -> None:
    graph = {1: [2], 2: [3], 3: []}
    order = lambda x, y: _reachable(graph, x, y) and x != y
    assert is_antichain(set(), order)
    assert is_antichain({2}, order)
