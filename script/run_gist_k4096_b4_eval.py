#!/usr/bin/env python3
"""Run the full-GIST K4096 B=4 original-top100 validation sweep."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path("/tmp/saq-run")
BIN = Path("/rwproject/kdd-db/kluaq/saq/bin")
REPORT = ROOT / "reports"
RESULT = ROOT / "results" / "saq"
DATE = "2026_07_04"
TAG = "k4096_original_top100"
NPROBES = [50, 100, 200, 400, 800]
QPS_NPROBE = 800

PLANS = [
    {
        "budget": 4,
        "name": "v2_split64",
        "category": "B4 best recall on K512/sample100k",
        "plan": "64:9,64:7,128:6,320:4,256:2,128:0",
    },
    {
        "budget": 4,
        "name": "filtered_new",
        "category": "B4 balanced on K512/sample100k",
        "plan": "64:10,320:6,384:3,192:0",
    },
]

DEFAULT = {"budget": 4, "name": "default_b4", "category": "default", "plan": ""}


def run(cmd: list[str], env: dict[str, str]) -> str:
    print("RUN", " ".join(cmd), flush=True)
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(proc.stdout, flush=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc.stdout


def parse_stdout(stdout: str) -> dict[str, str]:
    vals = {}
    for line in stdout.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            vals[key.strip()] = value.strip()
    return vals


def compact_plan(plan: str) -> str:
    if not plan:
        return ""
    return "_plan" + "_".join(token.replace(":", "x") for token in plan.split(","))


def qps_path(plan: str) -> Path:
    suffix = compact_plan(plan)
    return RESULT / (
        f"qps_gist_full_ivf4096_b4_caq_adj_seg{suffix}_pca_"
        f"th24_np{QPS_NPROBE}_sm4_safeblockminsimd.csv"
    )


def best_delta_from_csv(path: Path) -> tuple[int, int]:
    best_query = -1
    best_delta = 0
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            delta = int(row["delta_hits"])
            if delta > best_delta:
                best_delta = delta
                best_query = int(row["query_id"])
    return best_query, best_delta


def main() -> int:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = "/tmp/saq-deps/usr/lib64" + (
        ":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""
    )
    REPORT.mkdir(parents=True, exist_ok=True)
    RESULT.mkdir(parents=True, exist_ok=True)

    compare_rows = []
    recalls = {plan["name"]: {} for plan in PLANS}
    for item in PLANS:
        for nprobe in NPROBES:
            output = REPORT / (
                f"gist_full_{TAG}_B4_{item['name']}_"
                f"safeblockminsimd_compare_np{nprobe}_top100.csv"
            )
            stdout = run(
                [
                    str(BIN / "compare_search_results"),
                    "-dataset",
                    "gist_full",
                    "-K",
                    "4096",
                    "-B",
                    "4",
                    "-enable_PCA=true",
                    "-searcher_dist_type=0",
                    "-searcher_safe_block_min_mode=2",
                    "-compare_topk=100",
                    f"-compare_nprobe={nprobe}",
                    f"-seg_plan={item['plan']}",
                    f"-compare_output={output}",
                    "-logtostderr=1",
                ],
                env,
            )
            vals = parse_stdout(stdout)
            best_query, best_delta = best_delta_from_csv(output)
            row = {
                "budget": item["budget"],
                "name": item["name"],
                "category": item["category"],
                "plan": item["plan"],
                "nprobe": nprobe,
                "default_recall": float(vals["default_recall"]),
                "custom_recall": float(vals["custom_recall"]),
                "delta_recall": float(vals["delta_recall"]),
                "better_queries": int(vals["custom_better_queries"]),
                "equal_queries": int(vals["custom_equal_queries"]),
                "worse_queries": int(vals["custom_worse_queries"]),
                "worst_query": int(vals["worst_query"]),
                "worst_delta_hits": int(vals["worst_delta_hits"]),
                "best_query": best_query,
                "best_delta_hits": best_delta,
                "output": str(output),
            }
            compare_rows.append(row)
            recalls[item["name"]][nprobe] = row

    qps_info = {}
    for item in [DEFAULT] + PLANS:
        cmd = [
            str(BIN / "test_qps"),
            "-dataset",
            "gist_full",
            "-K",
            "4096",
            "-B",
            "4",
            "-enable_PCA=true",
            "-searcher_dist_type=0",
            "-searcher_safe_block_min_mode=2",
            "-qps_topk=100",
            f"-fix_nprobe={QPS_NPROBE}",
            "-fix_thread=24",
            "-logtostderr=1",
        ]
        if item["plan"]:
            cmd.append(f"-seg_plan={item['plan']}")
        run(cmd, env)
        expected = qps_path(item["plan"])
        tagged = expected.with_name(expected.stem + "_original_top100" + expected.suffix)
        shutil.copyfile(expected, tagged)
        with expected.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 1:
            raise ValueError(f"unexpected QPS rows in {expected}: {len(rows)}")
        qps_info[item["name"]] = {
            "qps": float(rows[0]["QPS"]),
            "avg_tm_ms": float(rows[0]["avg_tm_ms"]),
            "recall": float(rows[0]["recall"]),
            "output": str(tagged),
        }

    default_recalls = {}
    for nprobe in NPROBES:
        default_recalls[nprobe] = next(
            row["default_recall"] for row in compare_rows if row["nprobe"] == nprobe
        )

    leader_rows = []
    base_qps = qps_info["default_b4"]
    leader_rows.append(
        {
            "budget": 4,
            "name": "default_b4",
            "category": "default",
            "plan": "",
            **{f"recall_np{nprobe}": default_recalls[nprobe] for nprobe in NPROBES},
            **{f"delta_np{nprobe}": 0.0 for nprobe in NPROBES},
            "qps_np": QPS_NPROBE,
            "qps": base_qps["qps"],
            "avg_tm_ms": base_qps["avg_tm_ms"],
            "qps_recall": base_qps["recall"],
            "qps_ratio": 1.0,
            "np800_better_queries": 0,
            "np800_equal_queries": 1000,
            "np800_worse_queries": 0,
            "np800_worst_query": -1,
            "np800_worst_delta_hits": 0,
            "np800_best_query": -1,
            "np800_best_delta_hits": 0,
            "qps_output": base_qps["output"],
        }
    )

    for item in PLANS:
        plan_recalls = recalls[item["name"]]
        qps = qps_info[item["name"]]
        np800 = plan_recalls[800]
        leader_rows.append(
            {
                "budget": item["budget"],
                "name": item["name"],
                "category": item["category"],
                "plan": item["plan"],
                **{
                    f"recall_np{nprobe}": plan_recalls[nprobe]["custom_recall"]
                    for nprobe in NPROBES
                },
                **{
                    f"delta_np{nprobe}": plan_recalls[nprobe]["delta_recall"]
                    for nprobe in NPROBES
                },
                "qps_np": QPS_NPROBE,
                "qps": qps["qps"],
                "avg_tm_ms": qps["avg_tm_ms"],
                "qps_recall": qps["recall"],
                "qps_ratio": qps["qps"] / base_qps["qps"],
                "np800_better_queries": np800["better_queries"],
                "np800_equal_queries": np800["equal_queries"],
                "np800_worse_queries": np800["worse_queries"],
                "np800_worst_query": np800["worst_query"],
                "np800_worst_delta_hits": np800["worst_delta_hits"],
                "np800_best_query": np800["best_query"],
                "np800_best_delta_hits": np800["best_delta_hits"],
                "qps_output": qps["output"],
            }
        )

    leader_csv = REPORT / f"gist_full_k4096_original_top100_b4_leaderboard_{DATE}.csv"
    compare_csv = REPORT / f"gist_full_k4096_original_top100_b4_compare_rows_{DATE}.csv"
    leader_json = REPORT / f"gist_full_k4096_original_top100_b4_leaderboard_{DATE}.json"

    leader_fields = (
        ["budget", "name", "category", "plan"]
        + [f"recall_np{nprobe}" for nprobe in NPROBES]
        + [f"delta_np{nprobe}" for nprobe in NPROBES]
        + [
            "qps_np",
            "qps",
            "avg_tm_ms",
            "qps_recall",
            "qps_ratio",
            "np800_better_queries",
            "np800_equal_queries",
            "np800_worse_queries",
            "np800_worst_query",
            "np800_worst_delta_hits",
            "np800_best_query",
            "np800_best_delta_hits",
            "qps_output",
        ]
    )
    with leader_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=leader_fields)
        writer.writeheader()
        writer.writerows(leader_rows)

    compare_fields = [
        "budget",
        "name",
        "category",
        "plan",
        "nprobe",
        "default_recall",
        "custom_recall",
        "delta_recall",
        "better_queries",
        "equal_queries",
        "worse_queries",
        "worst_query",
        "worst_delta_hits",
        "best_query",
        "best_delta_hits",
        "output",
    ]
    with compare_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=compare_fields)
        writer.writeheader()
        writer.writerows(compare_rows)

    with leader_json.open("w", encoding="utf-8") as handle:
        json.dump(
            {"leaderboard": leader_rows, "compare_rows": compare_rows, "qps_nprobe": QPS_NPROBE},
            handle,
            indent=2,
        )
        handle.write("\n")

    print(f"WROTE {leader_csv}")
    print(f"WROTE {compare_csv}")
    print(f"WROTE {leader_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
