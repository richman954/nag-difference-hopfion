"""NAG Difference Hopfion benchmark package."""

from .scoring import score_terms, soft_selection_weights
from .pairwise import pairwise_difference_matrix, is_antisymmetric
from .hopfion_terms import load_barrier_table

__all__ = [
    "score_terms",
    "soft_selection_weights",
    "pairwise_difference_matrix",
    "is_antisymmetric",
    "load_barrier_table",
]
