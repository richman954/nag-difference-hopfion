# Formalization Roadmap

We maintain a staged path for formal verification:

1. Encode cancellation identity statements in Lean.
2. Add finite antichain/path lemmas for the chain-certificate layer.
3. Build small executable checks mirroring theorem preconditions.
4. Expand to richer statement libraries after stable API/tests.

The workflow is compatible with a decomposition style where tasks are partitioned into decomposition, translation, solving, and orchestration passes.
