import pytest
from nagdiff.cancellation import (
    cancellation_residual,
    certificate_difference,
    pairwise_specific_difference,
)


def test_shared_term_cancellation_identity():
    c = 12.5
    si = -0.4
    sj = 0.9
    assert certificate_difference(c, si, sj) == pytest.approx(pairwise_specific_difference(si, sj))


def test_zero_residual():
    assert cancellation_residual(3.2, 1.1, -7.3) == 0.0


def test_antisymmetry():
    left = pairwise_specific_difference(2.0, -5.0)
    right = pairwise_specific_difference(-5.0, 2.0)
    assert left == -right


def test_invariance_under_common_term_changes():
    si = 4.0
    sj = 1.0
    assert certificate_difference(0.0, si, sj) == certificate_difference(99.0, si, sj)
