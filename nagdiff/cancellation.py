from __future__ import annotations


def endpoint_difference(common: float, specific_i: float, specific_j: float) -> float:
    """Compute Phi_i - Phi_j with Phi_k = common + specific_k."""
    phi_i = common + specific_i
    phi_j = common + specific_j
    return phi_i - phi_j


def cancellation_certificate(common: float, specific_i: float, specific_j: float) -> bool:
    """Verify endpoint-cancellation identity (Phi_i-Phi_j)=(Specific_i-Specific_j)."""
    return endpoint_difference(common, specific_i, specific_j) == (specific_i - specific_j)
