# NAG Difference Core Theory

This project currently has two tracks:

- **Track A (physical benchmark):** pairwise endpoint/path comparison for FeGe laser-written hopfion state selection.
- **Track B (finite toy benchmark):** chain-certificate and antichain reasoning inspired by Erdős #1196 proof patterns.

## Endpoint certificates and pairwise matrix

For each candidate state, define an endpoint certificate. The pairwise object is:

\[
D_{ij}(\lambda) =
    [\mathrm{barrier}_i(\lambda) - \mathrm{barrier}_j(\lambda)]
    + \alpha [\mathrm{observable\_mismatch}_i(\lambda) - \mathrm{observable\_mismatch}_j(\lambda)]
    - \beta [\log(\mathrm{probability}_i(\lambda)+\delta) - \log(\mathrm{probability}_j(\lambda)+\delta)]
    + \gamma [\mathrm{topology\_penalty}_i - \mathrm{topology\_penalty}_j].
\]

Selection rule: state \(i\) beats state \(j\) when \(D_{ij}(\lambda) < 0\).

## Cancellation of shared terms

The key idea is subtraction of endpoint certificates.

### Theorem sketch (shared-term cancellation)

If \(\Phi_i = C + S_i\) and \(\Phi_j = C + S_j\), then
\[
\Phi_i - \Phi_j = (C + S_i) - (C + S_j) = S_i - S_j.
\]

So shared background terms cancel, and discrimination is carried by specific differences.

## Chain-certificate extension

Track B uses finite directed paths and antichains to represent mutually exclusive endpoint sets.

### Theorem sketch (antichain mutual exclusivity on a path)

If every admissible directed path hits a given antichain at most once, then that antichain behaves as a mutually exclusive endpoint set along those paths.

## Caution and scope

This repository is a framework and benchmark scaffold. It does **not** claim to prove that physical hopfions obey NAG Difference, and it does not claim a full proof of Erdős #1196.
