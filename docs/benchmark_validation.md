# What the barrier benchmark currently measures

## Does the score distinguish the observed barrier assignment?

Run `python -m nagdiff.benchmark_controls > controls.json` from the repository root. This replays the pinned publisher workbooks and passes their differences and the three rows of the scoring template to the repository's scoring function. It also sets all barriers to zero and evaluates all six assignments of the original barriers to the three paths at each conditional scale. [Template](../data/processed/nag_hopfion_scoring_template.csv) · [Control implementation](../nagdiff/benchmark_controls.py)

**All six assignments and the zero-barrier control rank merger first, collapse second and escape third.** Only the publisher assignment gives the same ordering for the full score and the barrier-only score. Each template auxiliary term already favors that ordering. With the original assignments, the energy term accounts for 0.06270% of the escape-minus-collapse score difference on the printed scale and 0.00006274% on the conditional SI scale. These are properties of the supplied weights and example inputs. Merger also starts in a different basin from the two loss routes.

### How many escapes would distinguish the two scores?

Restrict the softmax to the two exits from the hopfion. Use a 1 pJ energy reference and a dimensionless softmax temperature of 1 to reproduce the numerical barrier weighting of the example template. For a constant escape forecast `p` and observed escape fraction `q` among resolved runs, the mean binary Brier loss is `p² − 2pq + q`. Two distinct forecasts tie at the midpoint of their probabilities. This is a prespecified scoring criterion. It requires no outcome labels to compute.

| Conditional workbook scale | Full score, escape probability | Barrier-only, escape probability | Observed escape fraction at tie |
|---|---:|---:|---:|
| Printed pJ | 32.9318% | 49.9889% | 41.4603% |
| SI density | 32.9416% | 50.0000% (rounded) | 41.4708% |

At either scale, the full score earns a lower Brier loss **below** the corresponding threshold, and barrier-only earns a lower loss **above** it. For example, among ten resolved events at one matched condition, four escapes favor the full template and five favor barrier-only. These probabilities follow from the chosen weights, energy reference, and dimensionless softmax temperature. No escape frequency for the Chen sample has been established. The JSON control output includes the probabilities and exact crossover for the floating-point forecasts in each scenario.

### What would a thermal barrier model predict?

For stationary, isothermal competition between two exits from the same starting state, assume rates `kᵢ = νᵢ exp(−Bᵢ/kBT)`. At an illustrative 200 K the barrier gap alone gives the following results. The effective prefactors can include route-specific attempt frequencies and multiplicities. The command reports base-ten logarithms so small rate ratios retain their magnitude. [Code](../nagdiff/thermal_routes.py) · [Exact SI Boltzmann constant](https://physics.nist.gov/cuu/Constants/Value/k.html)

| Conditional workbook scale | (Escape − collapse barrier) / kBT | log₁₀(escape rate / collapse rate), equal prefactors |
|---|---:|---:|
| Printed pJ | 161,515.75 | −70,145.40 |
| SI density | 161.516 | −70.1454 |

Under the SI-density reading, equal rates would require an escape-to-collapse prefactor ratio of about 1.40 × 10⁷⁰ at that temperature. The two absolute scale readings therefore give very different quantitative consequences even though both put the escape saddle above collapse. The 200 K illustration holds the barriers fixed. Effective prefactors, the temperature history of a pulse and absolute lifetimes have not been measured here. The template's dimensionless softmax setting is independent of kelvin.

```sh
python -m nagdiff.thermal_routes --temperature-k 200
```

### A published case with unequal route prefactors

Kuchkin et al. plot both route-specific rates from harmonic transition-state theory and their activation-exponential contributions in Figure 4B. Digitizing the main panel and its inset at the same reduced temperature, `T/(J/kB) = 0.8`, tests how much the prefactors matter in that separate chiral-film calculation. Here `J` is the study's exchange-energy parameter. [Publication, section 3.4](https://doi.org/10.3389/fphy.2023.1201018) · [Credited crop and calibration](../data/raw/kuchkin_2023/SOURCE.md)

| Figure-derived comparison | Estimate | Pixel-position sensitivity |
|---|---:|---:|
| Escape/internal-decay rate ratio from full theory | 0.446 | 0.415–0.479 |
| Ratio from the barrier exponentials alone | 0.242 | 0.209–0.280 |
| Implied effective escape/decay prefactor ratio | 1.84 | 1.48–2.29 |

Converting odds to a share among the two routes gives 30.8% escape for the full transition-state theory and 19.5% for the barrier exponential alone. As a cross-check, adding the two read-off rates gives a lifetime of 1,241 reduced time units, versus 1,245 on the separately drawn total-lifetime curve. The ranges quantify changes from shifting the digitized positions within the stated pixel tolerances. All these values come from theoretical curves in the 2023 model. Neither these rates nor its prefactor ratio were used to fit the Chen template or generate a held-out outcome.

```sh
python scripts/check_kuchkin_rates.py
```

## How many sampled images recover the barrier?

Collapse and escape have 36 and 25 stored images, respectively. Their full-grid ratio from the density differences is 13,483/5,264 (about 2.56136). Use each image-index offset for strides 7 and 8, always retaining both endpoints. This gives 49 + 64 = 113 offset pairs. One refinement reads the unread images bracketing the highest visible sampled peak. The comparison allocates exactly the same number of reads to each path and repeatedly bisects the longest remaining gap.

| Method | Pairs with escape above collapse | Both published saddle images recovered | Ratio within 10% of full grid | Distinct image energies read per pair |
|---|---:|---:|---:|---:|
| Initial fixed-stride sample | 102/113 | 2/113 | 14/113 | 10–13 of 61 |
| Longest-gap midpoint | 113/113 | 32/113 | 60/113 | 33–40 of 61 |
| Refine around visible peak | 113/113 | 113/113 | 113/113 | 33–40 of 61 |

All offsets reuse the same two simulated paths. Read counts quantify access to stored energies. An independent path solver would also have to optimize the images. A synthetic regression puts a higher peak outside the chosen interval and shows exactly where local refinement can fail. [Regression tests](../tests/test_benchmark_controls.py)

## How to test route prediction on a new cohort

The intended target is the probability of escape among hopfions with a resolved escape or collapse during a prespecified observation window. The two published barrier paths provide input energies. To measure prediction quality, enroll repeated runs from the same starting basin under specified conditions and observation windows, retain each run's independent identifier and record every outcome. Kuchkin et al. report ten stochastic runs but publish two representative examples. The examples establish at least one escape and one internal decay among the ten. This bounds the fraction escaping among resolved runs to 10–90% even if some other runs were unresolved. The counts needed to narrow that bound were not reported in the checked public material. The two selected movies cannot be treated as a two-run sample. [Kuchkin et al., stochastic simulations](https://doi.org/10.3389/fphy.2023.1201018)

1. Before outcomes are available, prepare the plan using the schema below. Establish the roster in an independent enrollment record. Source route priors, observables, topology penalties, model coefficients, the energy reference and the common softmax temperature from theory or separate training data. Record their origin and the model version. Define censoring and the adjudication policy before unblinding.
2. Run `freeze` and record its printed SHA-256 in an independent, dated record before reading outcomes. Retain the plan and the frozen snapshot.
3. Obtain one outcome per enrolled condition/run/window, including censored and indeterminate cases. Score both models on exactly the same resolved events. Use the original independently recorded digest for the comparison.

```sh
python -m nagdiff.route_evaluation freeze plan.json predictions.json
python -m nagdiff.route_evaluation design predictions.json --snapshot-sha256 "$REGISTERED_SHA256"
python -m nagdiff.route_evaluation evaluate predictions.json outcomes.json --snapshot-sha256 "$REGISTERED_SHA256"
```

| File | Required fields |
|---|---|
| Plan | `protocol_id`, `cohort_design` = `all_enrolled`, `enrollment_source`, `feature_source`, `model`, `conditions` |
| Model | `energy_unit`, `energy_reference`, `temperature`, `alpha`, `beta`, `gamma`, `delta`. Reference, temperature and delta are positive. Both models divide the declared barrier by the same energy reference before scoring. |
| Each condition | `condition_id`, `window`, `run_ids`, `routes` containing `collapse` and `escape` |
| Each route | `barrier` in the declared energy unit, `observable_mismatch`, `prior_probability`, `topology_penalty` |
| Outcomes | `protocol_id`, `outcome_source` and `records`. Each record has `condition_id`, `run_id`, `window` and one `outcome` from `collapse`, `escape`, `censored`, `indeterminate`. |

The `design` command reads the pinned predictions alone. For each enrolled condition it reports the tie fraction and the direction in which either model would score better. When both forecasts are identical, every outcome fraction gives a tie.

The `evaluate` command reports paired binary Brier losses, coverage and outcome counts for each condition and for all resolved runs pooled. Its second summary weights each predeclared condition equally. If any enrolled condition has zero resolved runs, its mean and the equal-condition comparison are null. The original pooled result remains available whenever at least one run resolves. A negative full-minus-barrier-only difference favors the full model under the specified weighting. Neither summary estimates unconditional, time-dependent escape in the presence of censoring.

A synthetic regression enrolls nine runs in each of two conditions. All nine resolve in one condition and one resolves in the other. Pooling the ten events gives a paired difference of −0.025, while giving each condition equal weight gives +0.235. This illustrates why the target population and weighting should be specified before looking at results. These comparisons are descriptive and do not supply confidence intervals or establish independence among reused seeds.

The code checks structural validity, hashes and roster completeness relative to the submitted plan. External enrollment and data provenance establish whether that plan covers all runs, the features were independent of test labels, and the digest was recorded in time. Only synthetic fixtures have exercised the prospective model comparison. [Example plan, worked comparisons and tests](../tests/test_route_evaluation.py)

### Other public observations checked

The Chen Figure 3 workbook reports pulse-induced nucleation. Its Figure 4 workbook reports disappearance fields by plate thickness, with seven populated field values in Sheet1!C76:E78 and no internal-decay versus surface-escape labels. The distinct experiment by Lu et al. concerns driven hopfion-to-toron conversion and switching. A search of the cited papers and associated deposits identified no complete, condition-matched cohort suitable for scoring the two forecasts as of November 25, 2026. [Chen et al.](https://doi.org/10.1038/s41567-026-03236-0) · [Lu et al.](https://doi.org/10.1103/nwsq-s2p5) · [Kuchkin supplementary movie S1](https://doi.org/10.3389/fphy.2023.1201018.s001) · [Movie S2](https://doi.org/10.3389/fphy.2023.1201018.s002)
