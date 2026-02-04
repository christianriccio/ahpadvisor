import numpy as np

from src.ahp import aggregate_pairwise_matrices, build_pairwise_matrix, consistency_ratio, weights_geometric_mean


def test_build_matrix_and_weights():
    criteria = ["A", "B", "C"]
    comparisons = {("A", "B"): 3, ("A", "C"): 5, ("B", "C"): 2}
    mat = build_pairwise_matrix(criteria, comparisons)
    assert mat.shape == (3, 3)
    assert mat[0, 1] == 3
    assert np.isclose(mat[1, 0], 1 / 3)

    weights = weights_geometric_mean(mat)
    assert np.isclose(weights.sum(), 1.0)
    cr = consistency_ratio(mat, weights)
    assert cr >= 0


def test_aggregate_matrices():
    m1 = np.array([[1, 3, 5], [1 / 3, 1, 2], [1 / 5, 1 / 2, 1]])
    m2 = np.array([[1, 5, 7], [1 / 5, 1, 3], [1 / 7, 1 / 3, 1]])
    agg = aggregate_pairwise_matrices([m1, m2])
    assert agg.shape == (3, 3)
    assert np.isclose(agg[0, 1], np.sqrt(m1[0, 1] * m2[0, 1]))
