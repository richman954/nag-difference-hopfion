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

The following seeded values are **provisional placeholders** from prior notes, are **not final extracted values**, and are explicitly labeled as **raw MOESM verification pending**:

- `skyrmion_antiskyrmion_merge_to_hopfion`: `2.24e-4 pJ`
- `hopfion_collapse`: `2.86e-4 pJ`
- `hopfion_escape`: `7.32e-4 pJ`

See `data/processed/EXTRACTION_STATUS.md` for explicit extraction status.


## Authoritative barrier source data

The cited 2026 Nature Physics article publishes the relevant minimum-energy-path
simulation datasets as **Source Data Fig. 5** and **Source Data Extended Data
Fig. 9** XLSX files. Those publisher-provided workbooks are the authoritative
inputs for validating the three barrier paths used by this benchmark.

The current extraction module still contains legacy `MOESM13` / `MOESM16`
routing assumptions. Those names are not established as the publisher's source
data identifiers and should be treated as scaffold history, not provenance.
Do not rename unrelated files to satisfy that convention.

Until the actual source-data workbooks are downloaded, checksummed, mapped, and
validated, the full seeded table remains active with `seeded_fallback`
provenance. The seeded table is retained permanently for side-by-side audit
comparison.

See `docs/raw_extraction_protocol.md` and `CODEX_TASKS.md` for the current
authoritative-data checkpoint.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```


For reproducible extraction steps, see `docs/raw_extraction_protocol.md`.


## Second track: chain certificates

A second track now adds finite-state chain-certificate utilities for antichain and hitting-probability checks, plus starter formalization files under `formal/`.

## Checkpoints and visuals

We now track progress using explicit checkpoints and a lightweight pipeline visual:

- Checkpoints: `CHECKPOINTS.md`
- Visual map: `docs/progress_visuals.md`

At each checkpoint, run tests before proceeding.
