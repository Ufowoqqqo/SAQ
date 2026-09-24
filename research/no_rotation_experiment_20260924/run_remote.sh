#!/usr/bin/env bash
# Run on the already connected server. Does not fetch, train, commit or push.
set -euo pipefail
bundle=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=${1:-/rwproject/kdd-db/kluaq/worktrees/saq-data-aware-minimal-20260923}
output=${2:-$repo/results/no_rotation_2x2_2026_09_24}

if [[ ${NO_ROTATION_BOUNDED_RUN:-0} != 1 ]]; then
    mkdir -p -- "$(dirname -- "$output")"
    [[ ! -e "$output" ]] || { echo "Refusing existing output: $output" >&2; exit 1; }
    # One allowed CPU plus a one-hour wall cap bounds total compute well below
    # the prior two-CPU-hour ceiling, including child compilation and hashes.
    core=$(python3 -c 'import os; print(min(os.sched_getaffinity(0)))')
    exec /usr/bin/time -v -o "${output}.resources.txt" \
        timeout --signal=TERM --kill-after=15s 3600s \
        taskset -c "$core" env NO_ROTATION_BOUNDED_RUN=1 \
        OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
        OMP_THREAD_LIMIT=1 NUMEXPR_NUM_THREADS=1 \
        bash "$bundle/run_remote.sh" "$repo" "$output"
fi
ulimit -v 16777216
[[ ! -e "$output" ]] || { echo "Refusing existing output" >&2; exit 1; }
mkdir -p -- "$output"
printf 'RUNNING\n' > "$output/STATUS.txt"
trap 'rc=$?; if ((rc != 0)); then printf "BLOCKED_OR_FAILED exit=%s; inspect run.log\n" "$rc" > "$output/STATUS.txt"; fi' EXIT
exec > >(tee "$output/run.log") 2>&1
cd -- "$repo"
git status --short --branch
git rev-parse HEAD
date -u +%FT%TZ
uname -a
python3 --version
if [[ $(git rev-parse HEAD) != 35f38aa7ae668a4734d7a08a9bcf73aa00da9a75 ]]; then
    echo 'Repository HEAD differs from audited reference; inspect changes before running.' >&2
    exit 1
fi

# Model/input identity checks precede reading experiment panels.
sha256sum -c results/data_aware_rebuild_2026_09_23/sift_model_hashes.sha256
sha256sum -c results/data_aware_rebuild_2026_09_23/gist_model_hashes.sha256
python3 - "$repo" <<'PY'
import csv, hashlib, sys
from pathlib import Path
root = Path(sys.argv[1])
records = list(csv.DictReader((root/'results/data_aware_rebuild_2026_09_23/staged_inputs.tsv').open(), delimiter='\t'))
for row in records:
    if row['name'] not in ('sift_base.fvecs', 'gist_base.fvecs'):
        continue
    path = Path(row['source'])
    if path.stat().st_size != int(row['bytes']):
        raise RuntimeError(f'base size mismatch: {path}')
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else None
    if digest is None:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
        digest = h.hexdigest()
    if digest != row['sha256']: raise RuntimeError(f'base hash mismatch: {path}')
    print('PASS base hash', path)
for row in csv.DictReader((root/'results/data_aware_minimal_2026_09_23/inputs/recovered_indices.tsv').open(), delimiter='\t'):
    p = root/'results/data_aware_minimal_2026_09_23/inputs'/f"{row['dataset']}_indices.u64"
    if hashlib.sha256(p.read_bytes()).hexdigest() != row['sha256']:
        raise RuntimeError(f'index identity mismatch: {p}')
    print('PASS frozen indices', row['dataset'])
PY

faiss_library=${SAQ_FAISS_LIBRARY:-}
if [[ -z "$faiss_library" ]]; then
    for candidate in \
        "$repo/build/data-aware-minimal/faiss-build/faiss/libfaiss.a" \
        /tmp/saq-data-aware-rebuild-20260923/build/faiss-build/faiss/libfaiss.a; do
        if [[ -f "$candidate" ]]; then faiss_library=$candidate; break; fi
    done
fi
[[ -f "$faiss_library" ]] || { echo 'Cached libfaiss.a missing; set SAQ_FAISS_LIBRARY. No rebuild/download attempted.' >&2; exit 1; }
faiss_source=${SAQ_FAISS_SOURCE:-$repo/third_party/faiss}
blas_library=${SAQ_BLAS_LIBRARY:-/usr/lib64/libopenblaso.so.0}
[[ -f "$faiss_source/faiss/VectorTransform.h" && -f "$blas_library" ]] || { echo 'Faiss headers or BLAS missing' >&2; exit 1; }
sha256sum "$faiss_library" "$blas_library" > "$output/build_dependencies.sha256"
g++ --version
set -x
g++ -std=c++17 -O2 -fno-fast-math -ffp-contract=off -fopenmp \
    -I "$faiss_source" "$bundle/export_panels.cpp" "$faiss_library" \
    "$blas_library" -lpthread -o "$output/export_panels"
set +x
(cd -- "$bundle" && python3 -m unittest -v test_no_rotation)
for dataset in sift gist; do
    dimensions=128
    [[ "$dataset" != gist ]] || dimensions=960
    base=$(python3 - "$dataset" <<'PY'
import csv, sys
with open('results/data_aware_rebuild_2026_09_23/staged_inputs.tsv') as f:
    rows=list(csv.DictReader(f, delimiter='\t'))
print(next(r['source'] for r in rows if r['name']==sys.argv[1]+'_base.fvecs'))
PY
)
    "$output/export_panels" "$dimensions" "$base" \
        "results/data_aware_minimal_2026_09_23/inputs/${dataset}_indices.u64" \
        "results/data_aware_rebuild_2026_09_23/panels/$dataset" \
        "$output/panels/$dataset"
done
python3 "$bundle/no_rotation.py" --panels-root "$output/panels" --output "$output/measurement"
git diff --check
git status --short --branch
printf 'COMPLETE_ENCODER_DIAGNOSTIC; see measurement/summary.tsv and contrasts.tsv\n' > "$output/STATUS.txt"
date -u +%FT%TZ
