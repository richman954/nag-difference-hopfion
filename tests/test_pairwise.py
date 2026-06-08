from nagdiff.pairwise import is_antisymmetric, pairwise_difference_matrix


def test_antisymmetric_property():
    values = [0.1, 0.3, -0.2]
    d = pairwise_difference_matrix(values)
    assert is_antisymmetric(d)


def test_diagonal_zero():
    values = [1.0, 2.0, 3.0]
    d = pairwise_difference_matrix(values)
    assert all(abs(d[i][i]) < 1e-12 for i in range(len(values)))


def test_is_antisymmetric_non_square():
    # 2x3 matrix
    matrix = [[0.0, 1.0, 2.0], [-1.0, 0.0, -1.0]]
    assert not is_antisymmetric(matrix)


def test_is_antisymmetric_not_antisymmetric():
    # 2x2 matrix that is not antisymmetric
    matrix = [[0.0, 1.0], [1.0, 0.0]]
    assert not is_antisymmetric(matrix)
