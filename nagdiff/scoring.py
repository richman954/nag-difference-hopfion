from __future__ import annotations

import math
from typing import Iterable


def score_terms(
    barrier: Iterable[float],
    observable_mismatch: Iterable[float],
    probability: Iterable[float],
    topology_penalty: Iterable[float],
    alpha: float = 1.0,
    beta: float = 1.0,
    gamma: float = 1.0,
    delta: float = 1e-12,
) -> list[float]:
    """Compute per-state scalar score before pairwise differencing."""
    b = [float(x) for x in barrier]
    om = [float(x) for x in observable_mismatch]
    p = [float(x) for x in probability]
    tp = [float(x) for x in topology_penalty]
    return [
        b_i + alpha * om_i - beta * math.log(p_i + delta) + gamma * tp_i
        for b_i, om_i, p_i, tp_i in zip(b, om, p, tp)
    ]


def soft_selection_weights(scores: Iterable[float], temperature: float = 1.0) -> list[float]:
    """Convert scores to normalized selection weights; lower score => higher weight."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    s = [float(x) for x in scores]
    shifted = [-(x / temperature) for x in s]
    maxv = max(shifted)
    expv = [math.exp(x - maxv) for x in shifted]
    denom = sum(expv)
    return [x / denom for x in expv]
