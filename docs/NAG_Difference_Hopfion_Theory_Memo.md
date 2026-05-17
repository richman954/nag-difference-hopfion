# NAG Difference Hopfion Theory Memo

This memo tracks the initial mathematical framing for endpoint/path comparison-based state selection in FeGe hopfion nucleation studies.

Core comparison object:

\[
D_{ij}(\lambda) =
    [\mathrm{barrier}_i(\lambda) - \mathrm{barrier}_j(\lambda)]
    + \alpha [\mathrm{observable\_mismatch}_i(\lambda) - \mathrm{observable\_mismatch}_j(\lambda)]
    - \beta [\log(\mathrm{probability}_i(\lambda)+\delta) - \log(\mathrm{probability}_j(\lambda)+\delta)]
    + \gamma [\mathrm{topology\_penalty}_i - \mathrm{topology\_penalty}_j]
\]

Decision rule: state \(i\) beats state \(j\) when \(D_{ij}(\lambda) < 0\).

All seeded barrier values in this scaffold are **raw MOESM verification pending**.
