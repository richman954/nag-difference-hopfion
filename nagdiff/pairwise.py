from __future__ import annotations

import numpy as np
from typing import Iterable, Sequence


def pairwise_difference_matrix(values: Iterable[float]) -> list[list[float]]:
    """Return antisymmetric pairwise difference matrix D where D[i,j] = values[i] - values[j].

    Antisymmetry follows directly from subtraction:
    D[j,i] = values[j] - values[i] = -(values[i] - values[j]) = -D[i,j].
    """
    arr = np.fromiter(values, dtype=float)
    return np.subtract.outer(arr, arr).tolist()


def is_antisymmetric(matrix: Sequence[Sequence[float]], tol: float = 1e-12) -> bool:
    """Check whether matrix is antisymmetric within tolerance."""
    n = len(matrix)
    for i in range(n):
        if len(matrix[i]) != n:
            return False
        for j in range(n):
            if abs(float(matrix[i][j]) + float(matrix[j][i])) > tol:
                return False
    return True
