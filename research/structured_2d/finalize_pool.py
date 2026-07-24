#!/usr/bin/env python3
"""Validate the frozen query-free pool and write deterministic TSV manifests."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DATABASE_ROWS = 1_000_000
TARGET_BYTES = (32, 64)


@dataclass(frozen=True)
class Arm:
    dataset: str
    nlist: int
    arm_id: str
    artifact: Path
    transform: Path | None
    auxiliary: Path | None
    artifact_serialized_bytes: int
    routing_common_coarse_bytes: int
    external_routing_coarse_required: bool
    common_id_bytes: int
    packed_code_bytes: float
    build_cpu_seconds: float
    build_wall_seconds: float
    peak_rss_bytes: int

    @property
    def complete_system_bytes(self) -> int:
        return self.artifact_serialized_bytes + (
            self.routing_common_coarse_bytes
            if self.external_routing_coarse_required
            else 0
        )

    @property
    def method_bytes_per_vector(self) -> float:
        owned = (
            self.complete_system_bytes
            - self.routing_common_coarse_bytes
            - self.common_id_bytes
        )
        if owned < 0:
            raise ValueError(f"negative owned bytes for {self.arm_id}")
        return owned / DATABASE_ROWS


def physical_ids(dataset: str) -> set[str]:
    common = {
        "S128_B4",
        "S128_B8",
        "D128_B4",
        "D128_B8",
        "V128_B4",
        "V128_B8",
        "IVFFLAT",
        *(f"RABITQ_B{bits}" for bits in range(1, 5)),
        *(f"RABITQFS_B{bits}" for bits in range(1, 5)),
    }
    if dataset == "sift":
        return common | {
            "PQFULL_M32X8",
            "PQFULL_M64X4",
            "PQFULL_M64X8",
            "PQFULL_M128X4",
            "PQFSFULL_M64X4",
            "PQFSFULL_M128X4",
            "OPQFULL_M32X8",
            "OPQFULL_M64X4",
            "OPQFULL_M64X8",
            "OPQFULL_M128X4",
        }
    return common | {
        "PQ128_M32X8",
        "PQ128_M64X8",
        "OPQHEAD_M32X8",
        "OPQHEAD_M64X8",
        "PQFULL_M32X8",
        "PQFULL_M64X4",
        "PQFULL_M64X8",
        "PQFSFULL_M64X4",
        "OPQFULL_M32X8",
        "OPQFULL_M64X4",
        "OPQFULL_M64X8",
    }


def one_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != 1:
        raise ValueError(f"{path}: expected one resource row")
    return rows[0]


def number(row: dict[str, str], *names: str) -> float:
    for name in names:
        if name in row:
            return float(row[name])
    raise ValueError(f"missing any of {names}")


def sum_suffix(row: dict[str, str], suffix: str) -> float:
    values = [float(value) for key, value in row.items() if key.endswith(suffix)]
    if not values:
        raise ValueError(f"missing {suffix}")
    return sum(values)


def artifact_from_resource(path: Path) -> Path:
    suffix = ".resources.tsv"
    if not path.name.endswith(suffix):
        raise ValueError(f"bad resource suffix: {path}")
    return path.with_name(path.name[: -len(suffix)])


def read_arms(pool: Path) -> list[Arm]:
    arms: list[Arm] = []
    routing_coarse: dict[tuple[str, int], int] = {}
    rows: list[tuple[str, int, Path, dict[str, str]]] = []
    for dataset in ("sift", "gist"):
        for nlist in (1024, 4096):
            directory = pool / dataset / f"nlist_{nlist}"
            resources = sorted(directory.glob("*.resources.tsv"))
            observed = {
                artifact_from_resource(path).name.rsplit(".", 1)[0]
                for path in resources
            }
            expected = physical_ids(dataset)
            if observed != expected:
                raise ValueError(
                    f"{dataset}/{nlist} physical registry mismatch; "
                    f"missing={sorted(expected - observed)} "
                    f"extra={sorted(observed - expected)}"
                )
            for path in resources:
                row = one_row(path)
                rows.append((dataset, nlist, path, row))
                if artifact_from_resource(path).name == "IVFFLAT.faiss":
                    routing_coarse[(dataset, nlist)] = int(
                        row["common_coarse_bytes"]
                    )

    for dataset, nlist, resource, row in rows:
        artifact = artifact_from_resource(resource)
        if not artifact.is_file():
            raise ValueError(f"missing artifact: {artifact}")
        arm_id = artifact.name.rsplit(".", 1)[0]
        head_only = dataset == "gist" and arm_id.startswith(
            (
                "S128_",
                "D128_",
                "V128_",
                "PQ128_",
                "OPQHEAD_",
            )
        )
        transform = None
        if arm_id.startswith(("OPQFULL_", "OPQHEAD_")):
            transform = Path(f"{artifact}.opq.faiss")
            if not transform.is_file():
                raise ValueError(f"missing OPQ transform: {transform}")
        auxiliary = None
        if arm_id.startswith("D128_"):
            auxiliary = Path(f"{artifact}.radix.u16")
            if not auxiliary.is_file():
                raise ValueError(f"missing dyadic radix sidecar: {auxiliary}")
            if auxiliary.stat().st_size != 128:
                raise ValueError(
                    f"{arm_id}: radix sidecar is "
                    f"{auxiliary.stat().st_size} bytes, expected 128"
                )
        complete = int(
            number(row, "complete_serialized_bytes", "serialized_bytes")
        )
        resource_complete = artifact.stat().st_size
        if transform is not None:
            resource_complete += transform.stat().st_size
        if resource_complete != complete:
            raise ValueError(
                f"{arm_id}: serialized bytes {resource_complete} != {complete}"
            )
        actual_complete = resource_complete
        if auxiliary is not None:
            actual_complete += auxiliary.stat().st_size
        arms.append(
            Arm(
                dataset=dataset,
                nlist=nlist,
                arm_id=arm_id,
                artifact=artifact,
                transform=transform,
                auxiliary=auxiliary,
                artifact_serialized_bytes=actual_complete,
                routing_common_coarse_bytes=routing_coarse[(dataset, nlist)],
                external_routing_coarse_required=head_only,
                common_id_bytes=int(row["common_id_bytes"]),
                packed_code_bytes=number(
                    row, "packed_code_bytes_per_vector"
                ),
                build_cpu_seconds=sum_suffix(row, "_cpu_seconds"),
                build_wall_seconds=sum_suffix(row, "_wall_seconds"),
                peak_rss_bytes=int(row["peak_rss_bytes"]),
            )
        )
    return sorted(arms, key=lambda arm: (arm.dataset, arm.nlist, arm.arm_id))


def write_tsv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def bit_count(arm_id: str) -> int:
    return int(arm_id.rsplit("B", 1)[1])


def context_choice(candidates: list[Arm], target: int, lower: bool) -> Arm | None:
    eligible = [
        arm
        for arm in candidates
        if (arm.method_bytes_per_vector <= target)
        == lower
    ]
    if not eligible:
        return None

    def tie(arm: Arm) -> tuple[int, int, str]:
        return (
            bit_count(arm.arm_id),
            1 if arm.arm_id.startswith("RABITQFS_") else 0,
            arm.arm_id,
        )

    if lower:
        best_value = max(arm.method_bytes_per_vector for arm in eligible)
    else:
        best_value = min(arm.method_bytes_per_vector for arm in eligible)
    tied = [
        arm for arm in eligible if arm.method_bytes_per_vector == best_value
    ]
    return min(tied, key=tie)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    arms = read_arms(args.pool)
    write_tsv(
        args.output_directory / "pool_manifest.tsv",
        [
            "dataset",
            "nlist",
            "arm_id",
            "artifact",
            "transform",
            "auxiliary",
            "artifact_serialized_bytes",
            "external_routing_coarse_required",
            "routing_common_coarse_bytes",
            "complete_system_bytes",
            "common_id_bytes",
            "method_bytes_per_vector",
            "packed_code_bytes_per_vector",
            "build_cpu_seconds",
            "build_wall_seconds",
            "peak_rss_bytes",
        ],
        (
            {
                "dataset": arm.dataset,
                "nlist": arm.nlist,
                "arm_id": arm.arm_id,
                "artifact": arm.artifact,
                "transform": arm.transform or "",
                "auxiliary": arm.auxiliary or "",
                "artifact_serialized_bytes": arm.artifact_serialized_bytes,
                "external_routing_coarse_required": (
                    "true" if arm.external_routing_coarse_required else "false"
                ),
                "routing_common_coarse_bytes": (
                    arm.routing_common_coarse_bytes
                ),
                "complete_system_bytes": arm.complete_system_bytes,
                "common_id_bytes": arm.common_id_bytes,
                "method_bytes_per_vector": f"{arm.method_bytes_per_vector:.9f}",
                "packed_code_bytes_per_vector": f"{arm.packed_code_bytes:g}",
                "build_cpu_seconds": f"{arm.build_cpu_seconds:.9f}",
                "build_wall_seconds": f"{arm.build_wall_seconds:.9f}",
                "peak_rss_bytes": arm.peak_rss_bytes,
            }
            for arm in arms
        ),
    )

    alias_rows: list[dict[str, object]] = []
    for nlist in (1024, 4096):
        for alias, physical in (
            ("PQ128_M32X8", "PQFULL_M32X8"),
            ("PQ128_M64X8", "PQFULL_M64X8"),
            ("OPQ128_M32X8", "OPQFULL_M32X8"),
            ("OPQ128_M64X8", "OPQFULL_M64X8"),
        ):
            alias_rows.append(
                {
                    "dataset": "sift",
                    "nlist": nlist,
                    "logical_arm_id": alias,
                    "physical_arm_id": physical,
                    "reason": "SIFT full PCA view has exactly 128 dimensions",
                }
            )
    write_tsv(
        args.output_directory / "arm_aliases.tsv",
        ["dataset", "nlist", "logical_arm_id", "physical_arm_id", "reason"],
        alias_rows,
    )

    slot_rows: list[dict[str, object]] = []
    availability_rows: list[dict[str, object]] = []
    rates = {
        "sift": ("1.5", "2", "2.5", "3.5", "4", "4.5"),
        "gist": ("0.2", "4/15", "1/3", "0.4", "8/15", "2/3"),
    }
    unavailable_reason = (
        "frozen 76fb83a IVF::load nested cluster loop fails the required "
        "multi-cell save/load prerequisite; production source changes forbidden"
    )
    for dataset in ("sift", "gist"):
        for nlist in (1024, 4096):
            for family in ("SAQ", "CAQ"):
                for rate in rates[dataset]:
                    availability_rows.append(
                        {
                            "dataset": dataset,
                            "nlist": nlist,
                            "family": family,
                            "configuration": f"avg_bits={rate}",
                            "status": "UNAVAILABLE",
                            "reason": unavailable_reason,
                        }
                    )
                for target in TARGET_BYTES:
                    for side in ("LOW", "HIGH"):
                        slot_rows.append(
                            {
                                "dataset": dataset,
                                "nlist": nlist,
                                "family": family,
                                "target_bytes": target,
                                "side": side,
                                "status": "UNAVAILABLE",
                                "arm_id": "",
                                "method_bytes_per_vector": "",
                                "reason": unavailable_reason,
                            }
                        )

            candidates = [
                arm
                for arm in arms
                if arm.dataset == dataset
                and arm.nlist == nlist
                and arm.arm_id.startswith(("RABITQ_", "RABITQFS_"))
            ]
            if len(candidates) != 8:
                raise ValueError(f"{dataset}/{nlist}: RaBitQ pool size")
            for arm in candidates:
                availability_rows.append(
                    {
                        "dataset": dataset,
                        "nlist": nlist,
                        "family": "RABITQ",
                        "configuration": arm.arm_id,
                        "status": "AVAILABLE",
                        "reason": "",
                    }
                )
            for target in TARGET_BYTES:
                for side, lower in (("LOW", True), ("HIGH", False)):
                    choice = context_choice(candidates, target, lower)
                    slot_rows.append(
                        {
                            "dataset": dataset,
                            "nlist": nlist,
                            "family": "RABITQ",
                            "target_bytes": target,
                            "side": side,
                            "status": "AVAILABLE" if choice else "UNAVAILABLE",
                            "arm_id": choice.arm_id if choice else "",
                            "method_bytes_per_vector": (
                                f"{choice.method_bytes_per_vector:.9f}"
                                if choice
                                else ""
                            ),
                            "reason": "" if choice else "no serialized bracket",
                        }
                    )

    write_tsv(
        args.output_directory / "context_availability.tsv",
        ["dataset", "nlist", "family", "configuration", "status", "reason"],
        availability_rows,
    )
    write_tsv(
        args.output_directory / "context_slots.tsv",
        [
            "dataset",
            "nlist",
            "family",
            "target_bytes",
            "side",
            "status",
            "arm_id",
            "method_bytes_per_vector",
            "reason",
        ],
        slot_rows,
    )
    print(f"validated_arms\t{len(arms)}")
    print(f"manifest\t{args.output_directory / 'pool_manifest.tsv'}")
    print(f"context_slots\t{args.output_directory / 'context_slots.tsv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
