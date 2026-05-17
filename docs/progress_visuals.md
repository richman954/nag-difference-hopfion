# Progress Visuals

## Pipeline snapshot

```text
[data/raw/MOESM13*, MOESM16*]
              |
              v
   nagdiff.extraction.extract_barriers_from_raw
              |
              v
 write_extraction_artifact -> data/processed/extracted_barriers.json
              |
              v
   nagdiff.hopfion_terms.load_barrier_table
        /                         \
       /                           \
(extracted records)          (seeded fallback records)
       \                           /
        \                         /
         +----> pairwise/scoring workflows
```

## Checkpoint test ladder

```text
Checkpoint A: pairwise antisymmetry tests      -> pass required
Checkpoint B: scoring + fallback/extracted mode -> pass required
Checkpoint C: extraction artifact/provenance    -> pass required
```
