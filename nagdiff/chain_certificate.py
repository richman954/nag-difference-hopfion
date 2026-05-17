from __future__ import annotations

from collections import defaultdict


def validate_submarkov_rows(transition: dict[object, dict[object, float]], tol: float = 1e-12) -> bool:
    for row in transition.values():
        mass = sum(row.values())
        if mass - 1.0 > tol:
            return False
        if any(p < -tol for p in row.values()):
            return False
    return True


def generate_paths_dag(graph: dict[object, list[object]], start: object, max_depth: int = 10) -> list[list[object]]:
    paths: list[list[object]] = []

    def dfs(node: object, path: list[object], depth: int) -> None:
        nxt = graph.get(node, [])
        if depth >= max_depth or not nxt:
            paths.append(path.copy())
            return
        for v in nxt:
            if v in path:
                continue
            path.append(v)
            dfs(v, path, depth + 1)
            path.pop()

    dfs(start, [start], 0)
    return paths


def is_antichain(nodes: set[object], graph: dict[object, list[object]]) -> bool:
    reach = defaultdict(set)
    for s in graph:
        stack = [s]
        seen = set()
        while stack:
            u = stack.pop()
            for v in graph.get(u, []):
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        reach[s] = seen

    nlist = list(nodes)
    for i in range(len(nlist)):
        for j in range(i + 1, len(nlist)):
            a, b = nlist[i], nlist[j]
            if b in reach[a] or a in reach[b]:
                return False
    return True


def hits_antichain_at_most_once(path: list[object], antichain: set[object]) -> bool:
    return sum(1 for x in path if x in antichain) <= 1


def all_paths_hit_antichain_at_most_once(paths: list[list[object]], antichain: set[object]) -> bool:
    return all(hits_antichain_at_most_once(p, antichain) for p in paths)


def hitting_probability(paths: list[list[object]], path_probs: list[float], target: set[object]) -> float:
    hit = 0.0
    for p, pr in zip(paths, path_probs):
        if any(x in target for x in p):
            hit += pr
    if hit < 0:
        return 0.0
    if hit > 1:
        return 1.0
    return hit
