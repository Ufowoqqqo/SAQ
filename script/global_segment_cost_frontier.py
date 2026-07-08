#!/usr/bin/env python3
"""Offline risk-cost frontier for SAQ global segment plans.

This script reproduces SAQ's global variance DP, then computes deterministic
metric-specific Pareto frontiers over implementation-derived cost terms. It
does not use queries and does not build an index. The goal is to evaluate
whether a single global plan can reduce search-relevant segment cost without
introducing a weighted objective with unjustified coefficients.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

import numpy as np

K_DIM_PADDING_SIZE = 64
K_MAX_QUANT_BITS = 13
K_NUM_SHORT_FACTORS = 2
FLOAT_BITS = 32
SEGMENT_OVERHEAD_BITS = K_NUM_SHORT_FACTORS * FLOAT_BITS

Plan = tuple[tuple[int, int], ...]
CostValue = Union[int, float]

COST_METRICS = (
    "positive_dim",
    "accurate_extra_bit_volume",
    "total_code_bit_volume",
    "positive_segments",
    "segment_factor_bits",
    "zero_tail_risk",
)


@dataclass(frozen=True)
class Candidate:
    plan: Plan
    risk: float
    used_bits: int
    total_bits: int
    num_segments: int
    positive_segments: int
    positive_dim: int
    zero_tail_dim: int
    total_code_bit_volume: int
    accurate_extra_bit_volume: int
    segment_factor_bits: int
    zero_tail_risk: float


def metric_value(metric: str, block_sums: np.ndarray, start_block: int, end_block: int, bits: int) -> CostValue:
    dim = (end_block - start_block) * K_DIM_PADDING_SIZE
    if bits == 0:
        if metric == "zero_tail_risk":
            return float(block_sums[start_block:end_block].sum())
        return 0
    if metric == "positive_dim":
        return dim
    if metric == "accurate_extra_bit_volume":
        return dim * (bits - 1)
    if metric == "total_code_bit_volume":
        return dim * bits
    if metric == "positive_segments":
        return 1
    if metric == "segment_factor_bits":
        return SEGMENT_OVERHEAD_BITS
    if metric == "zero_tail_risk":
        return 0.0
    raise ValueError(f"unknown cost metric: {metric}")


def prune_state_map(states: dict[tuple[int, CostValue], float]) -> dict[tuple[int, CostValue], float]:
    items = [(used, cost, risk) for (used, cost), risk in states.items()]
    keep: dict[tuple[int, CostValue], float] = {}
    for idx, (used, cost, risk) in enumerate(items):
        dominated = False
        for j, (other_used, other_cost, other_risk) in enumerate(items):
            if idx == j:
                continue
            if other_used <= used and other_cost <= cost and other_risk <= risk:
                if other_used < used or other_cost < cost or other_risk < risk:
                    dominated = True
                    break
        if not dominated:
            key = (used, cost)
            previous = keep.get(key, math.inf)
            if risk < previous:
                keep[key] = risk
    return keep


def read_fvecs(path: Path) -> np.ndarray:
    raw = np.fromfile(path, dtype=np.int32)
    if raw.size == 0:
        raise ValueError(f"empty fvecs file: {path}")
    dim = int(raw[0])
    if dim <= 0:
        raise ValueError(f"bad fvecs dim {dim}: {path}")
    row_width = dim + 1
    if raw.size % row_width != 0:
        raise ValueError(f"{path} size is not divisible by fvecs row width")
    return raw.reshape(-1, row_width)[:, 1:].view(np.float32)


def pad_to_blocks(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    padded_dim = int(math.ceil(values.size / K_DIM_PADDING_SIZE) * K_DIM_PADDING_SIZE)
    if padded_dim == values.size:
        return values
    out = np.zeros(padded_dim, dtype=np.float64)
    out[: values.size] = values
    return out


def block_sums_from_variance(values: np.ndarray) -> np.ndarray:
    padded = pad_to_blocks(values)
    return padded.reshape(-1, K_DIM_PADDING_SIZE).sum(axis=1)


def compact_plan(plan: Plan) -> str:
    return ",".join(f"{dim}:{bits}" for dim, bits in plan)


def plan_used_bits(plan: Plan) -> int:
    used = 0
    for dim, bits in plan:
        if bits > 0:
            used += dim * bits + SEGMENT_OVERHEAD_BITS
    return used


def plan_risk(block_sums: np.ndarray, plan: Plan) -> float:
    risk = 0.0
    offset = 0
    for dim, bits in plan:
        nblocks = dim // K_DIM_PADDING_SIZE
        mass = float(block_sums[offset : offset + nblocks].sum())
        risk += mass if bits == 0 else mass / float(1 << bits)
        offset += nblocks
    return risk


def zero_tail_risk(block_sums: np.ndarray, plan: Plan) -> float:
    risk = 0.0
    offset = 0
    for dim, bits in plan:
        nblocks = dim // K_DIM_PADDING_SIZE
        if bits == 0:
            risk += float(block_sums[offset : offset + nblocks].sum())
        offset += nblocks
    return risk


def plan_stats(block_sums: np.ndarray, plan: Plan, total_bits: int) -> Candidate:
    positive_segments = sum(1 for _, bits in plan if bits > 0)
    positive_dim = sum(dim for dim, bits in plan if bits > 0)
    zero_tail_dim = sum(dim for dim, bits in plan if bits == 0)
    total_code_bit_volume = sum(dim * bits for dim, bits in plan if bits > 0)
    accurate_extra_bit_volume = sum(dim * (bits - 1) for dim, bits in plan if bits > 0)
    segment_factor_bits = positive_segments * SEGMENT_OVERHEAD_BITS
    return Candidate(
        plan=plan,
        risk=plan_risk(block_sums, plan),
        used_bits=plan_used_bits(plan),
        total_bits=total_bits,
        num_segments=len(plan),
        positive_segments=positive_segments,
        positive_dim=positive_dim,
        zero_tail_dim=zero_tail_dim,
        total_code_bit_volume=total_code_bit_volume,
        accurate_extra_bit_volume=accurate_extra_bit_volume,
        segment_factor_bits=segment_factor_bits,
        zero_tail_risk=zero_tail_risk(block_sums, plan),
    )


def enumerate_saq_final_states(block_sums: np.ndarray, avg_bits: float) -> tuple[list[Candidate], Candidate, int]:
    block_sums = np.asarray(block_sums, dtype=np.float64).reshape(-1)
    nblocks = int(block_sums.size)
    padded_dim = nblocks * K_DIM_PADDING_SIZE
    total_bits = int(avg_bits * padded_dim + SEGMENT_OVERHEAD_BITS)
    max_segments = nblocks if avg_bits < 2 else nblocks // 2

    states: list[list[dict[int, float]]] = [
        [dict() for _ in range(nblocks + 1)] for _ in range(max_segments + 1)
    ]
    parents: dict[tuple[int, int, int], tuple[int, int, int, int]] = {}
    states[0][0][0] = 0.0

    for ns in range(max_segments + 1):
        for i in range(nblocks + 1):
            for used_bits, prefix_risk in list(states[ns][i].items()):
                if i == nblocks or ns == max_segments:
                    continue

                var_sum = 0.0
                for j in range(1, nblocks - i + 1):
                    var_sum += float(block_sums[i + j - 1])
                    dim_len = j * K_DIM_PADDING_SIZE
                    for bits in range(1, K_MAX_QUANT_BITS + 1):
                        new_used = used_bits + bits * dim_len + SEGMENT_OVERHEAD_BITS
                        if new_used > total_bits:
                            break
                        new_risk = prefix_risk + var_sum / float(1 << bits)
                        key = (ns + 1, i + j, new_used)
                        current = states[ns + 1][i + j].get(new_used, math.inf)
                        if new_risk < current:
                            states[ns + 1][i + j][new_used] = new_risk
                            parents[key] = (ns, i, used_bits, bits)

                zero_risk = prefix_risk + var_sum
                key = (ns + 1, nblocks, used_bits)
                current = states[ns + 1][nblocks].get(used_bits, math.inf)
                if zero_risk < current:
                    states[ns + 1][nblocks][used_bits] = zero_risk
                    parents[key] = (ns, i, used_bits, 0)

    default_key: tuple[int, int, int] | None = None
    default_risk = math.inf
    for ns in range(max_segments + 1):
        for used_bits in range(total_bits + 1):
            risk = states[ns][nblocks].get(used_bits, math.inf)
            if risk * 1.01 < default_risk:
                default_key = (ns, nblocks, used_bits)
                default_risk = risk
    if default_key is None:
        raise RuntimeError("SAQ DP did not find a feasible default plan")

    seen_plans: dict[str, Candidate] = {}
    for ns in range(1, max_segments + 1):
        for used_bits, risk in states[ns][nblocks].items():
            if not math.isfinite(risk):
                continue
            plan = backtrack_plan(parents, (ns, nblocks, used_bits))
            stats = plan_stats(block_sums, plan, total_bits)
            plan_key = compact_plan(plan)
            previous = seen_plans.get(plan_key)
            if previous is None or stats.risk < previous.risk:
                seen_plans[plan_key] = stats

    candidates = list(seen_plans.values())
    candidates.sort(key=lambda c: (c.risk, c.used_bits, c.num_segments, compact_plan(c.plan)))
    default_plan = backtrack_plan(parents, default_key)
    default = plan_stats(block_sums, default_plan, total_bits)
    return candidates, default, total_bits


def metric_pareto_frontier(block_sums: np.ndarray, avg_bits: float, metric: str) -> tuple[list[Candidate], int]:
    block_sums = np.asarray(block_sums, dtype=np.float64).reshape(-1)
    nblocks = int(block_sums.size)
    padded_dim = nblocks * K_DIM_PADDING_SIZE
    total_bits = int(avg_bits * padded_dim + SEGMENT_OVERHEAD_BITS)
    max_segments = nblocks if avg_bits < 2 else nblocks // 2

    states: list[list[dict[tuple[int, CostValue], float]]] = [
        [dict() for _ in range(nblocks + 1)] for _ in range(max_segments + 1)
    ]
    parents: dict[
        tuple[int, int, int, CostValue],
        tuple[int, int, int, CostValue, int],
    ] = {}
    states[0][0][(0, 0.0 if metric == "zero_tail_risk" else 0)] = 0.0

    for ns in range(max_segments + 1):
        for i in range(nblocks + 1):
            state_items = list(states[ns][i].items())
            for (used_bits, cost), prefix_risk in state_items:
                if i == nblocks or ns == max_segments:
                    continue

                var_sum = 0.0
                for j in range(1, nblocks - i + 1):
                    end = i + j
                    var_sum += float(block_sums[end - 1])
                    dim_len = j * K_DIM_PADDING_SIZE
                    for bits in range(1, K_MAX_QUANT_BITS + 1):
                        new_used = used_bits + bits * dim_len + SEGMENT_OVERHEAD_BITS
                        if new_used > total_bits:
                            break
                        seg_cost = metric_value(metric, block_sums, i, end, bits)
                        new_cost = cost + seg_cost
                        new_risk = prefix_risk + var_sum / float(1 << bits)
                        target = states[ns + 1][end]
                        key = (new_used, new_cost)
                        current = target.get(key, math.inf)
                        if new_risk < current:
                            target[key] = new_risk
                            parents[(ns + 1, end, new_used, new_cost)] = (ns, i, used_bits, cost, bits)

                zero_cost = cost + metric_value(metric, block_sums, i, nblocks, 0)
                zero_risk = prefix_risk + var_sum
                target = states[ns + 1][nblocks]
                key = (used_bits, zero_cost)
                current = target.get(key, math.inf)
                if zero_risk < current:
                    target[key] = zero_risk
                    parents[(ns + 1, nblocks, used_bits, zero_cost)] = (ns, i, used_bits, cost, 0)

        if ns + 1 <= max_segments:
            for i in range(nblocks + 1):
                if len(states[ns + 1][i]) > 1:
                    states[ns + 1][i] = prune_state_map(states[ns + 1][i])

    final_states: dict[tuple[int, CostValue], tuple[float, tuple[int, int, int, CostValue]]] = {}
    for ns in range(1, max_segments + 1):
        for (used_bits, cost), risk in states[ns][nblocks].items():
            current = final_states.get((used_bits, cost))
            if current is None or risk < current[0]:
                final_states[(used_bits, cost)] = (risk, (ns, nblocks, used_bits, cost))

    raw: list[tuple[float, CostValue, tuple[int, int, int, CostValue]]] = []
    for (used_bits, cost), (risk, key) in final_states.items():
        raw.append((risk, cost, key))

    frontier_keys: list[tuple[int, int, int, CostValue]] = []
    for idx, (risk, cost, key) in enumerate(raw):
        dominated = False
        for j, (other_risk, other_cost, _) in enumerate(raw):
            if idx == j:
                continue
            if other_risk <= risk and other_cost <= cost:
                if other_risk < risk or other_cost < cost:
                    dominated = True
                    break
        if not dominated:
            frontier_keys.append(key)

    candidates: dict[str, Candidate] = {}
    for key in frontier_keys:
        plan = backtrack_metric_plan(parents, key)
        stats = plan_stats(block_sums, plan, total_bits)
        plan_key = compact_plan(plan)
        previous = candidates.get(plan_key)
        if previous is None or stats.risk < previous.risk:
            candidates[plan_key] = stats

    frontier = list(candidates.values())
    frontier.sort(key=lambda c: (getattr(c, metric), c.risk, c.used_bits, compact_plan(c.plan)))
    return frontier, total_bits


def backtrack_plan(
    parents: dict[tuple[int, int, int], tuple[int, int, int, int]],
    key: tuple[int, int, int],
) -> Plan:
    segments: list[tuple[int, int]] = []
    ns, i, used_bits = key
    while i > 0:
        prev_ns, prev_i, prev_used, bits = parents[(ns, i, used_bits)]
        segments.append(((i - prev_i) * K_DIM_PADDING_SIZE, bits))
        ns, i, used_bits = prev_ns, prev_i, prev_used
    segments.reverse()
    return tuple(segments)


def backtrack_metric_plan(
    parents: dict[
        tuple[int, int, int, CostValue],
        tuple[int, int, int, CostValue, int],
    ],
    key: tuple[int, int, int, CostValue],
) -> Plan:
    segments: list[tuple[int, int]] = []
    ns, i, used_bits, cost = key
    while i > 0:
        prev_ns, prev_i, prev_used, prev_cost, bits = parents[(ns, i, used_bits, cost)]
        segments.append(((i - prev_i) * K_DIM_PADDING_SIZE, bits))
        ns, i, used_bits, cost = prev_ns, prev_i, prev_used, prev_cost
    segments.reverse()
    return tuple(segments)


def dominates(a: Candidate, b: Candidate, metric: str) -> bool:
    a_cost = getattr(a, metric)
    b_cost = getattr(b, metric)
    return (a.risk <= b.risk and a_cost <= b_cost) and (a.risk < b.risk or a_cost < b_cost)


def pareto_frontier(candidates: list[Candidate], metric: str) -> list[Candidate]:
    frontier: list[Candidate] = []
    for cand in candidates:
        if any(dominates(other, cand, metric) for other in candidates):
            continue
        frontier.append(cand)
    frontier.sort(key=lambda c: (getattr(c, metric), c.risk, c.used_bits, compact_plan(c.plan)))
    return frontier


def candidate_to_row(candidate: Candidate) -> dict[str, Any]:
    return {
        "plan": compact_plan(candidate.plan),
        "risk": candidate.risk,
        "used_bits": candidate.used_bits,
        "total_bits": candidate.total_bits,
        "num_segments": candidate.num_segments,
        "positive_segments": candidate.positive_segments,
        "positive_dim": candidate.positive_dim,
        "zero_tail_dim": candidate.zero_tail_dim,
        "total_code_bit_volume": candidate.total_code_bit_volume,
        "accurate_extra_bit_volume": candidate.accurate_extra_bit_volume,
        "segment_factor_bits": candidate.segment_factor_bits,
        "zero_tail_risk": candidate.zero_tail_risk,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def risk_ratio(risk: float, reference: float) -> float:
    if reference == 0.0:
        return math.inf if risk > 0.0 else 1.0
    return risk / reference


def lower_cost_tradeoff(frontier: list[Candidate], default: Candidate, metric: str) -> dict[str, Any] | None:
    default_cost = getattr(default, metric)
    lower_cost = [cand for cand in frontier if getattr(cand, metric) < default_cost]
    if not lower_cost:
        return None

    lowest_risk = min(lower_cost, key=lambda c: (c.risk, getattr(c, metric), compact_plan(c.plan)))
    lowest_cost = min(lower_cost, key=lambda c: (getattr(c, metric), c.risk, compact_plan(c.plan)))
    return {
        "lowest_risk_lower_cost": getattr(lowest_risk, metric),
        "lowest_risk_lower_cost_plan": compact_plan(lowest_risk.plan),
        "lowest_risk_lower_cost_risk": lowest_risk.risk,
        "lowest_risk_lower_cost_risk_ratio": risk_ratio(lowest_risk.risk, default.risk),
        "minimum_cost": getattr(lowest_cost, metric),
        "minimum_cost_plan": compact_plan(lowest_cost.plan),
        "minimum_cost_risk": lowest_cost.risk,
        "minimum_cost_risk_ratio": risk_ratio(lowest_cost.risk, default.risk),
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    vars_vec = read_fvecs(Path(args.vars_file))
    if vars_vec.shape[0] != 1:
        raise ValueError(f"expected one variance vector, got shape {vars_vec.shape}")
    block_sums = block_sums_from_variance(vars_vec[0])
    candidates, default, total_bits = enumerate_saq_final_states(block_sums, args.avg_bits)
    if not candidates:
        raise RuntimeError("no feasible global segment plans found")
    exact_min_risk = min(candidates, key=lambda c: c.risk)

    output_prefix = Path(args.output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)

    all_rows = []
    for cand in candidates:
        row = candidate_to_row(cand)
        row["is_saq_default"] = compact_plan(cand.plan) == compact_plan(default.plan)
        row["is_exact_min_risk"] = compact_plan(cand.plan) == compact_plan(exact_min_risk.plan)
        all_rows.append(row)
    write_csv(output_prefix.with_suffix(".candidates.csv"), all_rows)

    frontier_summary: dict[str, Any] = {}
    frontier_rows: list[dict[str, Any]] = []
    for metric in COST_METRICS:
        frontier, _ = metric_pareto_frontier(block_sums, args.avg_bits, metric)
        dominating_default = [cand for cand in frontier if dominates(cand, default, metric)]
        no_worse_risk = [cand for cand in frontier if cand.risk <= default.risk]
        best_cost_no_worse = min(no_worse_risk, key=lambda c: (getattr(c, metric), c.risk, compact_plan(c.plan)))
        lower_cost = lower_cost_tradeoff(frontier, default, metric)
        frontier_summary[metric] = {
            "frontier_size": len(frontier),
            "default_dominated": bool(dominating_default),
            "dominating_default_count": len(dominating_default),
            "default_cost": getattr(default, metric),
            "best_cost_with_no_worse_risk": getattr(best_cost_no_worse, metric),
            "best_cost_with_no_worse_risk_plan": compact_plan(best_cost_no_worse.plan),
            "best_cost_with_no_worse_risk_risk": best_cost_no_worse.risk,
            "lower_cost_tradeoff": lower_cost,
        }
        for rank, cand in enumerate(frontier):
            row = candidate_to_row(cand)
            row["metric"] = metric
            row["frontier_rank"] = rank
            row["is_saq_default"] = compact_plan(cand.plan) == compact_plan(default.plan)
            frontier_rows.append(row)
    write_csv(output_prefix.with_suffix(".frontier.csv"), frontier_rows)

    summary = {
        "case": args.case,
        "vars_file": str(Path(args.vars_file)),
        "avg_bits": args.avg_bits,
        "num_candidates": len(candidates),
        "num_blocks": int(block_sums.size),
        "padded_dim": int(block_sums.size * K_DIM_PADDING_SIZE),
        "total_bits": total_bits,
        "saq_default": candidate_to_row(default),
        "exact_min_risk": candidate_to_row(exact_min_risk),
        "frontier_summary": frontier_summary,
        "paths": {
            "candidates_csv": str(output_prefix.with_suffix(".candidates.csv")),
            "frontier_csv": str(output_prefix.with_suffix(".frontier.csv")),
            "summary_json": str(output_prefix.with_suffix(".summary.json")),
            "summary_md": str(output_prefix.with_suffix(".md")),
        },
    }
    output_prefix.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_markdown(output_prefix.with_suffix(".md"), summary)
    return summary


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    default = summary["saq_default"]
    exact = summary["exact_min_risk"]
    lines = [
        "# Global Segment-Cost Frontier",
        "",
        f"- case: `{summary['case']}`",
        f"- variance file: `{summary['vars_file']}`",
        f"- average bits: {summary['avg_bits']}",
        f"- padded dimension: {summary['padded_dim']}",
        f"- total bit budget: {summary['total_bits']}",
        f"- feasible final plans: {summary['num_candidates']}",
        "",
        "## SAQ Default",
        "",
        f"- plan: `{default['plan']}`",
        f"- risk: {default['risk']:.8g}",
        f"- used bits: {default['used_bits']} / {default['total_bits']}",
        f"- positive segments: {default['positive_segments']}",
        f"- positive dim: {default['positive_dim']}",
        f"- accurate extra-bit volume: {default['accurate_extra_bit_volume']}",
        f"- zero-tail risk: {default['zero_tail_risk']:.8g}",
        "",
        "## Exact Minimum-Risk State",
        "",
        f"- plan: `{exact['plan']}`",
        f"- risk: {exact['risk']:.8g}",
        f"- used bits: {exact['used_bits']} / {exact['total_bits']}",
        "",
        "## No-Worse-Risk Cost Checks",
        "",
        "| metric | default dominated? | default cost | best cost at no worse risk | lowest-risk lower-cost ratio | lower-cost plan |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for metric in COST_METRICS:
        item = summary["frontier_summary"][metric]
        lower = item["lower_cost_tradeoff"]
        lower_ratio = "n/a"
        lower_plan = "n/a"
        if lower is not None:
            lower_ratio = f"{lower['lowest_risk_lower_cost_risk_ratio']:.6g}"
            lower_plan = f"`{lower['lowest_risk_lower_cost_plan']}`"
        lines.append(
            "| {metric} | {dominated} | {default_cost} | {best_cost} | {lower_ratio} | {lower_plan} |".format(
                metric=metric,
                dominated=str(item["default_dominated"]),
                default_cost=item["default_cost"],
                best_cost=item["best_cost_with_no_worse_risk"],
                lower_ratio=lower_ratio,
                lower_plan=lower_plan,
            )
        )
    lines.extend(
        [
            "",
            "## Output Artifacts",
            "",
            f"- candidates: `{summary['paths']['candidates_csv']}`",
            f"- frontier: `{summary['paths']['frontier_csv']}`",
            f"- summary: `{summary['paths']['summary_json']}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline SAQ global risk-cost frontier.")
    parser.add_argument("--case", required=True, help="Case label used in summaries.")
    parser.add_argument("--vars-file", required=True, help="One-row .fvecs variance file.")
    parser.add_argument("--avg-bits", type=float, required=True, help="SAQ average bit budget.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for CSV/JSON/Markdown artifacts.")
    return parser.parse_args()


def main() -> None:
    summary = analyze(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
