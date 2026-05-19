# NAG-Difference Core Theory

The core cancellation identity used in this repository is

\[
(C + S_i) - (C + S_j) = S_i - S_j.
\]

This expresses the pairwise principle that shared context terms cancel, leaving only discriminative terms between candidate endpoints.

## Minimal certificate functions

- `certificate_difference(C, S_i, S_j)` computes the full left-hand side.
- `pairwise_specific_difference(S_i, S_j)` computes the reduced right-hand side.
- `cancellation_residual(...)` returns the identity residual and is expected to be zero.
