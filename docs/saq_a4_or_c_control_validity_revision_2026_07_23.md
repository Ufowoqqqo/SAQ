# A4-OR-C control-validity revision

Status: authorized on 2026-07-23 for the synthetic admission only.

This is a narrow correction to the P and V control-validity definition. It is
not a new research direction, does not alter the D or A algorithms, and grants
no access to natural datasets, benchmark queries, ground truth, or indexes.

## Why the rule changed

The original run stopped because Faiss reported an empty-cluster split during
P training. The bounded postmortem showed that these were intermediate repair
events: after training and final reassignment, all 768 inspected redo models
had no empty assigned center and no duplicate center, and the selected P
models encoded every synthetic row.

The old result at commit `67009a8` remains `CONTROL_INVALID`. Its contract,
artifacts, condition order, and result are historical evidence and are not
rewritten or retroactively reclassified.

## Revised P/V validity rule

For each selected final P or V model at both frozen rates:

1. **Shape:** the number of blocks, block dimensions, center counts, and center
   storage must exactly match the frozen P or V definition.
2. **Encoding:** final assignment must produce one in-range label for every
   synthetic row and every block. The total must equal rows times blocks.
3. **Final occupancy:** after assigning every training row to its final center,
   every center must have at least one assigned row.
4. **Center collision:** no two final centers in one block may have identical
   binary32 coordinate vectors.

The first failing check is reported in this order:

```text
P_shape
V_shape
P_encoding
V_encoding
P_final_occupancy
V_final_occupancy
P_center_collision_zero
V_center_collision_zero
```

Faiss `nsplit` remains in the output as an optimizer diagnostic. A nonzero
intermediate split count is not itself a validity failure.

All seeds, restarts, iteration caps, shapes, input rows, D/A methods, numerical
checks, thresholds, and later admission conditions remain unchanged. The
revision may rerun only the deterministic 8,192-by-128 synthetic admission
within the existing one-process, one-thread, 16-GiB boundary.

## Decision boundary

Passing these four final-model checks only establishes that P and V are usable
controls. It does not establish the A4 hypothesis. Sensitivity, near-tie,
resource, timing, and projected-cost checks still have to pass before any
synthetic admission can be reported as successful. Natural-data work remains
unauthorized.
