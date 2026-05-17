"""Endpoint-certificate cancellation utilities for NAG Difference."""

from __future__ import annotations

from typing import Iterable


Number = float | int


def _as_float_list(values: Iterable[Number]) -> list[float]:
    return [float(v) for v in values]


def certificate_difference(common_i: Number, specific_i: Number, common_j: Number, specific_j: Number) -> float:
    """Compute Phi_i - Phi_j where Phi_k = common_k + specific_k."""
    phi_i = float(common_i) + float(specific_i)
    phi_j = float(common_j) + float(specific_j)
    return phi_i - phi_j


def cancellation_residual(common: Number, specific_i: Number, specific_j: Number) -> float:
    """Return residual of (C+S_i)-(C+S_j) - (S_i-S_j), expected to be zero."""
    lhs = certificate_difference(common, specific_i, common, specific_j)
    rhs = float(specific_i) - float(specific_j)
    return lhs - rhs


def pairwise_specific_difference(specific_values: Iterable[Number]) -> list[list[float]]:
    """Return antisymmetric pairwise matrix D_ij = s_i - s_j for specific terms."""
    vals = _as_float_list(specific_values)
    return [[vals[i] - vals[j] for j in range(len(vals))] for i in range(len(vals))]
