# What the barrier benchmark currently measures

## Does the score distinguish the observed barrier assignment?

Run `python -m nagdiff.benchmark_controls > controls.json` from the repository root. This replays the pinned publisher workbooks and passes their differences and the three rows of the scoring template to the repository's scoring function. It also sets all barriers to zero and evaluates all six assignments of the original barriers to the three paths at each conditional scale. [Template](../data/processed/nag_hopfion_scoring_template.csv) · [Control implementation](../nagdiff/benchmark_controls.py)

**All six assignments and the zero-barrier control rank merger first, collapse second and escape third.** Only the publisher assignment gives the same ordering for the full score and the barrier-only score. Each template auxiliary term already favors that ordering. With the original assignments, the energy term accounts for 0.06270% of the escape-minus-collapse score difference on the printed scale and 0.00006274% on the conditional SI scale. These are properties of the supplied weights and example inputs. Merger also starts in a different basin from the two loss routes.

## How many sampled images recover the barrier?

Collapse and escape have 36 and 25 stored images, respectively. Their full-grid ratio from the density differences is 13,483/5,264 (about 2.56136). Use each image-index offset for strides 7 and 8, always retaining both endpoints. This gives 49 + 64 = 113 offset pairs. One refinement reads the unread images bracketing the highest visible sampled peak. The comparison allocates exactly the same number of reads to each path and repeatedly bisects the longest remaining gap.

| Method | Pairs with escape above collapse | Both published saddle images recovered | Ratio within 10% of full grid | Distinct image energies read per pair |
|---|---:|---:|---:|---:|
| Initial fixed-stride sample | 102/113 | 2/113 | 14/113 | 10–13 of 61 |
| Longest-gap midpoint | 113/113 | 32/113 | 60/113 | 33–40 of 61 |
| Refine around visible peak | 113/113 | 113/113 | 113/113 | 33–40 of 61 |

All offsets reuse the same two simulated paths. Read counts quantify access to stored energies. An independent path solver would also have to optimize the images. A synthetic regression puts a higher peak outside the chosen interval and shows exactly where local refinement can fail. [Regression tests](../tests/test_benchmark_controls.py)

## How to test route prediction on a new cohort

The intended target is the probability of escape among hopfions with a resolved escape or collapse during a prespecified observation window. The two published barrier paths provide input energies. To measure prediction quality, enroll repeated runs from the same starting basin under specified conditions and observation windows, retain each run's independent identifier and record every outcome. Kuchkin et al. report ten stochastic runs but publish two representative examples. Those examples do not give a complete set of outcomes. [Kuchkin et al., stochastic simulations](https://doi.org/10.3389/fphy.2023.1201018)

1. Before outcomes are available, prepare the plan using the schema below. Establish the roster in an independent enrollment record. Source route priors, observables, topology penalties, model coefficients, the energy reference and the common softmax temperature from theory or separate training data. Record their origin and the model version. Define censoring and the adjudication policy before unblinding.
2. Run `freeze` and record its printed SHA-256 in an independent, dated record before reading outcomes. Retain the plan and the frozen snapshot.
3. Obtain one outcome per enrolled condition/run/window, including censored and indeterminate cases. Score both models on exactly the same resolved events. Use the original independently recorded digest for the comparison.

```sh
python -m nagdiff.route_evaluation freeze plan.json predictions.json
python -m nagdiff.route_evaluation evaluate predictions.json outcomes.json --snapshot-sha256 "$REGISTERED_SHA256"
```

| File | Required fields |
|---|---|
| Plan | `protocol_id`, `cohort_design` = `all_enrolled`, `enrollment_source`, `feature_source`, `model`, `conditions` |
| Model | `energy_unit`, `energy_reference`, `temperature`, `alpha`, `beta`, `gamma`, `delta`. Reference, temperature and delta are positive. Both models divide the declared barrier by the same energy reference before scoring. |
| Each condition | `condition_id`, `window`, `run_ids`, `routes` containing `collapse` and `escape` |
| Each route | `barrier` in the declared energy unit, `observable_mismatch`, `prior_probability`, `topology_penalty` |
| Outcomes | `protocol_id`, `outcome_source` and `records`. Each record has `condition_id`, `run_id`, `window` and one `outcome` from `collapse`, `escape`, `censored`, `indeterminate`. |

The evaluator reports coverage, outcome counts, per-run binary Brier losses and their paired mean difference (full minus barrier-only). A negative difference favors the full model on the observed resolved events. Censored and indeterminate runs contribute to coverage. With zero resolved outcomes, both mean losses are null. The code checks hashes and roster completeness relative to the submitted plan. External enrollment and data provenance establish whether that plan covers all runs, the features were independent of test labels, and the digest was recorded in time. Only synthetic fixtures have exercised this evaluator. [Full example and tests](../tests/test_route_evaluation.py)
