#!/usr/bin/env python3
"""Snapshot GNU-time accounting; does not launch work or infer missing costs."""
import csv
from datetime import datetime, timezone
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
RESERVE_CPU_SECONDS = 240
CPU_LIMIT_SECONDS = 7200


def field(text, name):
    match = re.search(r"^\s*" + re.escape(name) + r":\s*(.*)$", text, re.M)
    return match.group(1).strip() if match else ""


def write_tsv(path, rows):
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    timestamp = datetime.now(timezone.utc).isoformat()
    seen, rows = set(), []
    for directory in sorted(RESULTS.glob("data_aware*")):
        for path in sorted(directory.rglob("*resources*.txt")):
            info = path.stat()
            identity = (info.st_dev, info.st_ino)
            duplicate = identity in seen
            seen.add(identity)
            text = path.read_text()
            user = field(text, "User time (seconds)")
            system = field(text, "System time (seconds)")
            exit_status = field(text, "Exit status")
            rss = field(text, "Maximum resident set size (kbytes)")
            complete = bool(user and system and exit_status)
            cpu = float(user) + float(system) if user and system else None
            status = ("COMPLETED_SUCCESS" if exit_status == "0" else "COMPLETED_NONZERO") if complete else "UNFINALIZED_ACTIVE_OR_INTERRUPTED"
            rows.append({"resource_log": str(path.relative_to(RESULTS)), "status": status,
                         "exit_status": exit_status, "cpu_seconds": "" if cpu is None else f"{cpu:.2f}",
                         "counted_in_completed_total": int(complete and not duplicate),
                         "duplicate_inode": int(duplicate), "peak_rss_bytes": int(rss) * 1024 if rss else "",
                         "wall_elapsed": field(text, "Elapsed (wall clock) time (h:mm:ss or m:ss)"),
                         "command": field(text, "Command being timed")})
    counted = [row for row in rows if row["counted_in_completed_total"]]
    cpu = sum(float(row["cpu_seconds"]) for row in counted)
    max_rss = max((row["peak_rss_bytes"] for row in counted), default=0)
    unfinalized = sum(row["status"] == "UNFINALIZED_ACTIVE_OR_INTERRUPTED" for row in rows)
    summary = [{"snapshot_utc": timestamp, "completed_gnu_time_records": len(counted),
                "completed_cpu_seconds": f"{cpu:.2f}", "unmetered_cpu_reserve_seconds": RESERVE_CPU_SECONDS,
                "completed_plus_reserve_seconds": f"{cpu + RESERVE_CPU_SECONDS:.2f}",
                "allowance_after_completed_and_reserve_seconds": f"{CPU_LIMIT_SECONDS - cpu - RESERVE_CPU_SECONDS:.2f}",
                "largest_reported_job_rss_bytes": max_rss, "unfinalized_resource_logs": unfinalized}]
    write_tsv(HERE / "resource_accounting.tsv", rows)
    write_tsv(HERE / "resource_accounting_summary.tsv", summary)
    (HERE / "resource_accounting_notes.txt").write_text(
        "Scope: all data_aware* result directories in this worktree, including earlier recovery attempts.\n"
        "Sum each completed GNU time record once by filesystem inode; retries and repeated tests count separately.\n"
        "Do not add diagnostic resources.tsv or per-arm compute times to GNU-time wrappers: these overlap.\n"
        "Empty/unfinished resource logs are active-or-interrupted, not completed zero-cost work. Their consumed CPU is unknown until GNU time closes.\n"
        "240 CPU seconds is the configured reserve for unmetered commands; it is an allowance, not a measured cost or proof all unknown work fits.\n"
        "Remaining allowance excludes currently active unreported CPU and must be recomputed before another job starts.\n"
        "GNU time records are rounded to 0.01 seconds. Failed or timed-out commands still consume CPU and are included.\n"
        "Largest reported RSS is the largest single-job GNU-time maximum, not aggregate simultaneous task RSS.\n"
        "Summing wall durations would double-count overlaps; elapsed recovery deadline is enforced separately.\n"
        "Read-only snapshot is not a completion assertion or an experimental decision.\n")
    for key, value in summary[0].items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
