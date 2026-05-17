"""Finite toy chain-certificate helpers inspired by Erdős #1196 patterns."""

from __future__ import annotations

from collections import defaultdict


def row_masses(kernel: dict[object, dict[object, float]]) -> dict[object, float]:
    return {state: float(sum(transitions.values())) for state, transitions in kernel.items()}


def validate_submarkov_kernel(kernel: dict[object, dict[object, float]], tol: float = 1e-12) -> bool:
    for state, transitions in kernel.items():
        mass = float(sum(transitions.values()))
        if mass > 1.0 + tol:
            return False
        for nxt, prob in transitions.items():
            if prob < -tol:
                return False
            if nxt == state and prob > tol:
                # self-loops are allowed mathematically, but excluded in this DAG toy model.
                return False
    return True


def generate_paths(graph: dict[object, list[object]], start: object, max_depth: int | None = None) -> list[list[object]]:
    paths: list[list[object]] = []

    def dfs(node: object, path: list[object]) -> None:
        neighbors = graph.get(node, [])
        if not neighbors or (max_depth is not None and len(path) - 1 >= max_depth):
            paths.append(path.copy())
            return
        for nxt in neighbors:
            if nxt in path:
                continue
            path.append(nxt)
            dfs(nxt, path)
            path.pop()

    dfs(start, [start])
    return paths


def is_antichain(elements: set[object], order_relation) -> bool:
    elems = list(elements)
    for i in range(len(elems)):
        for j in range(i + 1, len(elems)):
            a, b = elems[i], elems[j]
            if order_relation(a, b) or order_relation(b, a):
                return False
    return True


def path_hits_subset(path: list[object], subset: set[object]) -> bool:
    return any(node in subset for node in path)


def path_hits_subset_at_most_once(path: list[object], subset: set[object]) -> bool:
    return sum(1 for node in path if node in subset) <= 1


def all_paths_hit_antichain_at_most_once(paths: list[list[object]], antichain: set[object]) -> bool:
    return all(path_hits_subset_at_most_once(path, antichain) for path in paths)


def hitting_probabilities(
    kernel: dict[object, dict[object, float]],
    initial_distribution: dict[object, float],
    max_steps: int = 100,
) -> dict[object, float]:
    hit_probs = defaultdict(float)
    current = defaultdict(float, {k: float(v) for k, v in initial_distribution.items()})

    for state, mass in current.items():
        hit_probs[state] += mass

    for _ in range(max_steps):
        nxt = defaultdict(float)
        active_mass = 0.0
        for state, mass in current.items():
            transitions = kernel.get(state, {})
            row_mass = sum(transitions.values())
            if row_mass <= 0:
                continue
            for to_state, prob in transitions.items():
                contrib = mass * prob
                if contrib > 0:
                    nxt[to_state] += contrib
                    hit_probs[to_state] += contrib
                    active_mass += contrib
        current = nxt
        if active_mass <= 1e-15:
            break

    clamped: dict[object, float] = {}
    for state, prob in hit_probs.items():
        clamped[state] = min(max(prob, 0.0), 1.0)
    return clamped
