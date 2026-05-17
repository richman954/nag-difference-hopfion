from nagdiff.cancellation import (
    cancellation_residual,
    certificate_difference,
    pairwise_specific_difference,
)


def test_shared_common_terms_cancel_for_floats() -> None:
    assert certificate_difference(10.0, 3.5, 10.0, -1.25) == 4.75


def test_cancellation_residual_zero_with_identical_common_terms() -> None:
    assert cancellation_residual(7.0, 2.0, -5.0) == 0.0


def test_pairwise_specific_difference_is_antisymmetric() -> None:
    matrix = pairwise_specific_difference([1.0, 3.0, -2.0])
    n = len(matrix)
    for i in range(n):
        assert matrix[i][i] == 0.0
        for j in range(n):
            assert matrix[i][j] == -matrix[j][i]


def test_pairwise_result_unchanged_when_shared_common_term_changes() -> None:
    before = certificate_difference(1.0, 4.0, 1.0, -3.0)
    after = certificate_difference(1000.0, 4.0, 1000.0, -3.0)
    assert before == after
