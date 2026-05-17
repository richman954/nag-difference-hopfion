"""NAG Difference Hopfion benchmark package."""

from .scoring import score_terms, soft_selection_weights
from .pairwise import pairwise_difference_matrix, is_antisymmetric
from .hopfion_terms import load_barrier_table
from .reporting import write_extraction_comparison_csv
from .pipeline import run_checkpoint_pipeline
from .verification import evaluate_extraction_gate, write_extraction_status
from .cancellation import certificate_difference, cancellation_residual, pairwise_specific_difference
from .chain_certificate import (
    validate_submarkov_kernel,
    row_masses,
    generate_paths,
    is_antichain,
    path_hits_subset,
    path_hits_subset_at_most_once,
    all_paths_hit_antichain_at_most_once,
    hitting_probabilities,
)

__all__ = [
    "score_terms",
    "soft_selection_weights",
    "pairwise_difference_matrix",
    "is_antisymmetric",
    "load_barrier_table",
    "write_extraction_comparison_csv",
    "run_checkpoint_pipeline",
    "evaluate_extraction_gate",
    "write_extraction_status",
    "certificate_difference",
    "cancellation_residual",
    "pairwise_specific_difference",
    "validate_submarkov_kernel",
    "row_masses",
    "generate_paths",
    "is_antichain",
    "path_hits_subset",
    "path_hits_subset_at_most_once",
    "all_paths_hit_antichain_at_most_once",
    "hitting_probabilities",
]
