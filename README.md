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

Both publisher workbooks are included with their original filenames and SHA-256 receipts. The Figure 5 and Extended Data Figure 9 download links serve identical bytes. The extractor reproduces the three directed, sampled barriers. The workbook and plot label energy in pJ, while the spreadsheet formula would give fJ for an SI density input. Physical pJ validation remains open. The escape-to-collapse ratio is **2.56136** under either common scale. [Extraction status, cells and results](data/processed/EXTRACTION_STATUS.md) · [Publication](https://doi.org/10.1038/s41567-026-03236-0)

The scoring template gives the same ranking with every barrier assignment, including when all barriers are zero. For the two loss routes, the full template ties barrier-only at about 41.5% observed escape among resolved events and ties a prior-only control at about 35.2%. The template priors are illustrative. The benchmark also quantifies thermal sensitivity to the open energy scale and reports model performance by condition when held-out outcomes are supplied. [Benchmark results and replay](docs/benchmark_validation.md)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
python -m nagdiff.extraction
python -m nagdiff.benchmark_controls > controls.json
```

[Workbook extraction protocol](docs/raw_extraction_protocol.md)

## Second track: chain certificates

A second track now adds finite-state chain-certificate utilities for antichain and hitting-probability checks, plus starter formalization files under `formal/`.

## Checkpoints and visuals

We now track progress using explicit checkpoints and a lightweight pipeline visual:

- Checkpoints: `CHECKPOINTS.md`
- Visual map: `docs/progress_visuals.md`

At each checkpoint, run tests before proceeding.
