"""Cancellation helpers for pairwise NAG-difference identities."""

from __future__ import annotations


def certificate_difference(common_term: float, specific_i: float, specific_j: float) -> float:
    """Return ``(C + S_i) - (C + S_j)`` for explicit cancellation checks."""
    return (common_term + specific_i) - (common_term + specific_j)


def cancellation_residual(common_term: float, specific_i: float, specific_j: float) -> float:
    """Residual of cancellation identity, should be numerically zero."""
    lhs = certificate_difference(common_term, specific_i, specific_j)
    rhs = pairwise_specific_difference(specific_i, specific_j)
    return lhs - rhs


def pairwise_specific_difference(specific_i: float, specific_j: float) -> float:
    """Return the discriminative term ``S_i - S_j``."""
    return specific_i - specific_j
