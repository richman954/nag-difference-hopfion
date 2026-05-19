"""Finite-state chain certificate helpers for antichain hit checks."""

from __future__ import annotations

from itertools import product
from typing import Iterable


State = str
Kernel = dict[State, dict[State, float]]


def row_masses(kernel: Kernel) -> dict[State, float]:
    return {state: sum(transitions.values()) for state, transitions in kernel.items()}


def validate_submarkov_kernel(kernel: Kernel, tol: float = 1e-12) -> bool:
    for transitions in kernel.values():
        if any(weight < -tol for weight in transitions.values()):
            return False
        if sum(transitions.values()) > 1.0 + tol:
            return False
    return True


def generate_paths(kernel: Kernel, start: State, steps: int) -> list[list[State]]:
    if steps < 0:
        raise ValueError("steps must be non-negative")
    paths = [[start]]
    for _ in range(steps):
        extended: list[list[State]] = []
        for path in paths:
            tail = path[-1]
            next_states = list(kernel.get(tail, {}).keys())
            if not next_states:
                extended.append(path)
                continue
            for nxt in next_states:
                extended.append(path + [nxt])
        paths = extended
    return paths


def is_antichain(nodes: Iterable[State], order_pairs: set[tuple[State, State]]) -> bool:
    node_list = list(nodes)
    for i, a in enumerate(node_list):
        for b in node_list[i + 1 :]:
            if (a, b) in order_pairs or (b, a) in order_pairs:
                return False
    return True


def path_hits_subset(path: list[State], subset: set[State]) -> bool:
    return any(state in subset for state in path)


def path_hits_subset_at_most_once(path: list[State], subset: set[State]) -> bool:
    return sum(1 for state in path if state in subset) <= 1


def all_paths_hit_antichain_at_most_once(
    paths: list[list[State]], antichain: set[State]
) -> bool:
    return all(path_hits_subset_at_most_once(path, antichain) for path in paths)


def hitting_probabilities(
    kernel: Kernel,
    start_distribution: dict[State, float],
    target_subset: set[State],
    steps: int,
) -> float:
    if steps < 0:
        raise ValueError("steps must be non-negative")
    if not validate_submarkov_kernel(kernel):
        raise ValueError("kernel is not sub-Markov")

    current = start_distribution.copy()
    total_hit = 0.0
    for _ in range(steps + 1):
        hit_now = sum(prob for state, prob in current.items() if state in target_subset)
        total_hit += hit_now
        next_dist: dict[State, float] = {}
        for state, prob in current.items():
            if state in target_subset:
                continue
            for nxt, weight in kernel.get(state, {}).items():
                next_dist[nxt] = next_dist.get(nxt, 0.0) + prob * weight
        current = next_dist
    return total_hit
