# Full GIST K4096 B=4 Middle-Role Analysis

Date: 2026-07-06

## 1. Purpose

Before the next meeting, this note checks whether the existing full GIST K4096
B=4 v3/conservative sweep already contains a usable "middle" role between the
two raw Pareto endpoints:

```text
recall endpoint = v2_split64
speed endpoint  = compact_k4096
```

This is an offline CSV analysis only. It does not build or evaluate a new index.

Input artifact:

```text
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_conservative_sweep_2026_07_06.unique.csv
```

## 2. Candidate Set

The sweep produced six unique feasible plans:

| rank | plan | recall-risk score | speed proxy ratio | soft inversion ratio | weighted ratio |
|---:|---|---:|---:|---:|---:|
| 0 | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | 0.976507 | 0.976729 |
| 1 | `128:9,384:5,320:2,128:0` | 0.933510 | 0.784726 | 0.981194 | 0.981372 |
| 2 | `64:9,64:7,128:6,320:4,256:2,128:0` | 0.918630 | 1.215274 | 0.971267 | 0.971540 |
| 3 | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 1.000000 | 0.971205 | 0.971478 |
| 4 | `64:9,256:6,256:4,256:2,128:0` | 0.952862 | 1.000000 | 0.955130 | 0.955555 |
| 5 | `64:9,192:6,320:4,320:2,64:0` | 0.968741 | 1.005534 | 0.985056 | 0.985198 |

The measured balanced plan:

```text
filtered_new = 64:10,320:6,384:3,192:0
```

is not present in this v3 unique candidate set.

## 3. Upper-Bound Speed Selector

First check the simple middle selector proposed in the stage synthesis:

```text
minimize recall-risk score subject to speed_proxy_ratio <= threshold
```

Result:

| speed threshold | selected plan | recall-risk score | speed proxy ratio | readout |
|---:|---|---:|---:|---|
| 0.80 | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | compact speed endpoint |
| 0.90 | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | compact speed endpoint |
| 1.00 | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | compact speed endpoint |
| 1.05 | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | compact speed endpoint |
| 1.10 | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | compact speed endpoint |
| 1.20 | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | compact speed endpoint |

This selector does not create a middle point. It collapses to the speed endpoint
because `compact_k4096` already has the best recall-risk score among all plans
that are not slower than default.

## 4. Speed-Window Selector

Next check a stricter "middle" interpretation:

```text
minimize recall-risk score inside a default-speed window
```

Result:

| speed window | selected plan | recall-risk score | speed proxy ratio | soft inversion ratio |
|---|---|---:|---:|---:|
| `[0.90, 1.10]` | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 1.000000 | 0.971205 |
| `[0.95, 1.05]` | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 1.000000 | 0.971205 |
| `[0.98, 1.02]` | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 1.000000 | 0.971205 |
| `[1.00, 1.05]` | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 1.000000 | 0.971205 |

This does produce a non-endpoint candidate, but it is still not `filtered_new`.
It is a default-speed candidate from the existing DP output.

## 5. Target-Speed Penalty Selector

A smooth variant is:

```text
score = recall_risk_score + lambda * abs(speed_proxy_ratio - 1)
```

Result:

| lambda | selected plan | recall-risk score | speed proxy ratio | readout |
|---:|---|---:|---:|---|
| 0.01 | `64:9,64:7,128:6,320:4,256:2,128:0` | 0.918630 | 1.215274 | recall endpoint still wins |
| 0.05 | `64:9,64:7,128:6,320:4,256:2,128:0` | 0.918630 | 1.215274 | recall endpoint still wins |
| 0.10 | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 1.000000 | default-speed candidate |
| 0.20 | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 1.000000 | default-speed candidate |
| 0.50 | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 1.000000 | default-speed candidate |
| 1.00 | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 1.000000 | default-speed candidate |

This confirms that a target-speed objective can move away from the slow recall
endpoint, but the available DP candidate set still does not contain the measured
balanced shape.

## 6. Readout

The meeting-relevant conclusion is:

```text
The current v3 candidate generator can expose endpoints, but the existing
candidate set does not contain filtered_new.
```

Simple role-selection changes alone are not enough:

- `speed_proxy <= threshold` selects `compact_k4096`, not a middle point.
- default-speed windows select `64:8,192:7,320:4,256:2,128:0`, not
  `filtered_new`.
- `filtered_new` is absent from the six unique plans produced by this sweep.

This sharpens the next gap:

```text
The missing piece is candidate generation or shape prior, not just role
selection.
```

## 7. Implication For The Next Step

The next technical attempt should not be another scalar role over the same
candidate table. It should change what the planner can generate.

Promising options:

1. Add a middle-shape prior that favors a compact head plus broad mid/tail
   segments, closer to `filtered_new`.
2. Add a target-speed DP penalty directly during plan generation, not only
   during role selection.
3. Seed or constrain the DP with known balanced shape families and test whether
   the data-only pair-risk proxy ranks them sensibly.

For the meeting, the concise statement is:

```text
v3 has useful endpoint diagnostics, and the conservative guard prevents unsafe
promotion. The unresolved contribution gap is generating measured-balanced
plans like filtered_new, which the current DP sweep does not produce.
```
