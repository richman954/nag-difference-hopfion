# NAG Difference Hopfion Benchmark

This repository is a **research-code scaffold** for testing a NAG-Difference / endpoint-comparison state-selection idea in the FeGe laser-written hopfion case study.

## In plain language

Instead of asking "which state has the lowest standalone energy?", this benchmark asks:

- If we compare two candidate outcomes directly,
- along their barriers, observables, probabilities, and topology penalties,
- which one wins the pairwise contest?

That pairwise mindset is encoded by the antisymmetric comparison quantity
\(D_{ij}(\lambda)\), where state \(i\) beats state \(j\) when \(D_{ij}(\lambda) < 0\).

## Scientific framing

Candidate states include:

- helix/cone
- skyrmion
- antiskyrmion
- skyrmion-antiskyrmion pair
- hopfion
- bobber
- composite textures

The benchmark is based on **laser-induced hopfion nucleation in FeGe**.

## Core mathematical object

\[
D_{ij}(\lambda) =
    [\mathrm{barrier}_i(\lambda) - \mathrm{barrier}_j(\lambda)]
    + \alpha [\mathrm{observable\_mismatch}_i(\lambda) - \mathrm{observable\_mismatch}_j(\lambda)]
    - \beta [\log(\mathrm{probability}_i(\lambda)+\delta) - \log(\mathrm{probability}_j(\lambda)+\delta)]
    + \gamma [\mathrm{topology\_penalty}_i - \mathrm{topology\_penalty}_j]
\]

State \(i\) beats state \(j\) when \(D_{ij}(\lambda) < 0\).


## Why this is NAG Difference

The core object is a **difference between two candidate endpoints/paths**:

- We compare state *i* against state *j* directly through `D_ij(lambda)`.
- Shared background terms cancel when taking differences, so the model emphasizes discriminative contrasts rather than absolute baselines.
- This is why benchmark decisions are expressed as pairwise wins/losses (`D_ij < 0`) instead of a simple absolute-energy ranking.

## Seeded barriers (placeholder, provisional)

The following seeded values are **provisional placeholders** from prior notes and are **not final extracted values**:

- `skyrmion_antiskyrmion_merge_to_hopfion`: `2.24e-4 pJ`
- `hopfion_collapse`: `2.86e-4 pJ`
- `hopfion_escape`: `7.32e-4 pJ`

See `data/processed/EXTRACTION_STATUS.md` for explicit extraction status.


## Raw MOESM extraction behavior

`load_barrier_table()` attempts extraction from `data/raw/MOESM13*` and `data/raw/MOESM16*` CSV files first.
Only states with successful extraction replace seeded fallback values; otherwise provisional seeded values are retained with `seeded_fallback` provenance fields.
The seeded table is always kept available for side-by-side comparison and auditability.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```


For reproducible extraction steps, see `docs/raw_extraction_protocol.md`.


## Checkpoints and visuals

We now track progress using explicit checkpoints and a lightweight pipeline visual:

- Checkpoints: `CHECKPOINTS.md`
- Visual map: `docs/progress_visuals.md`

At each checkpoint, run tests before proceeding.
