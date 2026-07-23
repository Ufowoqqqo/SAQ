# A4-OR-C synthetic admission result

Status: `CONTROL_INVALID`

First failed condition: `P_nsplit_zero`

## Frozen execution

- Source commit: `1cf7a07f4cd22f57f0ee7c6256461cdcf9bbba0a`
- Faiss commit: `0ca9df4792b173d573044ee14ca0704780176e82`
- Input: only the deterministic 8,192-by-128 synthetic panel
- Process/thread policy: one process, one thread, logical CPU 0
- Environment: `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`,
  `MKL_NUM_THREADS=1`, `OMP_DYNAMIC=FALSE`
- Command:

```bash
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  OMP_DYNAMIC=FALSE taskset -c 0 \
  /tmp/a4-or-c-build/a4_or_c_synthetic
```

The formal warmup returned:

```text
warmup=0 passed=0 failure=P_nsplit_zero eta=2.84217e-14
eta_limit=0.000197833 sensitivity=1 near_tie=1 finite=1
allocation_order=1 shapes=1,1 collisions=0,0,0,0
nsplit=2855,8061
cpu_us=2119987610,98483,96645,81563821,48193985
support_cpu_us=11037 wall_us=2253922963 peak_rss_bytes=210255872
```

The P count is a nonzero witness, not a claim that 2,855 clusters were empty
simultaneously. Faiss reported actual split events during its frozen eight-redo
training. Any one such event fails the registered P control rule.

Conditions through P center collision passed. `P_nsplit_zero` failed. By the
frozen condition order, V nsplit, all-arms completion, sensitivity, near-tie,
memory, support ratio, projected time, and A-specific ratio are `NOT_RUN`.
Therefore no three measured timing repetitions were executed and no timing
artifact exists.

The printed floating-point diagnostics use the executable's default decimal
precision. The failed numeric artifact deliberately omits reconstructed
hexfloat values rather than presenting rounded log text as exact binary64
evidence. This does not affect the P split failure.

No natural data, benchmark query, ground truth, index, or previous A4 outcome
artifact was read. This result rejects the frozen control configuration only;
it is not evidence about natural-data quality, Recall, QPS, or SAQ improvement.

## Postmortem

The P-control postmortem is recorded in
`docs/saq_a4_or_c_progress_2026_07_23.md`. It found that Faiss's split events
were intermediate empty-cluster repairs: all 768 inspected final redo models
had zero empty assignments and zero duplicate centers, and both P rates
encoded every synthetic row successfully. This does not alter the committed
`CONTROL_INVALID` result.
