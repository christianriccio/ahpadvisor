import json
from typing import Dict, List, Tuple

import numpy as np


SAATY_SCALE = [1, 3, 5, 7, 9]
RI_TABLE = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.9, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def build_pairwise_matrix(criteria: List[str], comparisons: Dict[Tuple[str, str], float]) -> np.ndarray:
    n = len(criteria)
    idx = {c: i for i, c in enumerate(criteria)}
    mat = np.ones((n, n), dtype=float)
    for (a, b), value in comparisons.items():
        i = idx[a]
        j = idx[b]
        mat[i, j] = float(value)
        mat[j, i] = 1.0 / float(value)
    return mat


def weights_geometric_mean(matrix: np.ndarray) -> np.ndarray:
    if matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Pairwise matrix must be square")
    gm = np.prod(matrix, axis=1) ** (1.0 / matrix.shape[0])
    weights = gm / gm.sum()
    return weights


def consistency_ratio(matrix: np.ndarray, weights: np.ndarray) -> float:
    n = matrix.shape[0]
    if n <= 2:
        return 0.0
    aw = matrix @ weights
    lambda_max = np.mean(aw / weights)
    ci = (lambda_max - n) / (n - 1)
    ri = RI_TABLE.get(n, 1.49)
    if ri == 0:
        return 0.0
    return ci / ri


def aggregate_pairwise_matrices(matrices: List[np.ndarray]) -> np.ndarray:
    if not matrices:
        raise ValueError("No matrices to aggregate")
    stacked = np.stack(matrices, axis=0)
    return np.prod(stacked, axis=0) ** (1.0 / stacked.shape[0])


def matrix_to_json(matrix: np.ndarray) -> str:
    return json.dumps(matrix.tolist())


def matrix_from_json(data: str) -> np.ndarray:
    return np.array(json.loads(data), dtype=float)
