#!/usr/bin/env bash
set -eu
cd /rwproject/kdd-db/kluaq/worktrees/saq-data-aware-minimal-20260923
out=results/data_aware_minimal_2026_09_23
exec > "$out/audit.log" 2>&1
set -x
date -Is
hostname
pwd
git rev-parse HEAD
git status --short --branch
git -C /rwproject/kdd-db/kluaq/archive/projects/ann/saq status --short --branch
git -C /rwproject/kdd-db/kluaq/archive/projects/ann/saq rev-parse HEAD
git worktree list
nproc
free -b
df -B1 . /tmp
cat /proc/loadavg
sed -n '/Cpus_allowed_list/p; /Mems_allowed_list/p' /proc/self/status
python3 -c 'import platform, numpy; print("python=" + platform.python_version()); print("numpy=" + numpy.__version__)'
find /tmp/correlated-pair-allocation /tmp/saq-correlated-pair-allocation -maxdepth 5 -type f -printf '%p\t%s bytes\n'
for dataset in sift gist; do
    for object in "stages-v2/$dataset/residual_nlist1024.fvecs" "stages-v2/$dataset/STAGE_SOURCE.txt" "indices/${dataset}_indices.u64" "common/$dataset/pca.faiss" "common/$dataset/base_pca.fvecs" "common/$dataset/nlist_1024/coarse.faiss" "common/$dataset/nlist_1024/base_assignments.u32"; do
        stat --printf='%n\t%s bytes\n' "/tmp/correlated-pair-allocation/$object" || true
    done
done
stat --printf='%n\t%s bytes\n' /rwproject/kdd-db/kluaq/dataset/sift1m/sift_base.fvecs /rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs
python3 - <<'PY'
from pathlib import Path
import hashlib
import numpy as np
from research.correlated_pair_allocation.diagnostic import sample_indices

output = Path('results/data_aware_minimal_2026_09_23/inputs')
expected = (
    ('sift', 'a5ef3954b0d240e9b5fcf59690a559d458b6f05b7c55ca3c0e6bdb648c61a104'),
    ('gist', '5cb6868406e6f184abe689058992ab9e8aba52a312c64aa34345a51e7826966d'),
)
with (output / 'recovered_indices.tsv').open('w') as log:
    log.write('dataset\trows\tsha256\thistorical_hash_matches\tunique_rows\tfit_eval_overlap\n')
    for offset, (name, target) in enumerate(expected):
        indices = np.asarray(sample_indices(offset), dtype='<u8')
        digest = hashlib.sha256(indices.tobytes()).hexdigest()
        overlap = np.intersect1d(indices[:8192], indices[8192:]).size
        assert digest == target and len(np.unique(indices)) == 16384 and overlap == 0
        indices.tofile(output / (name + '_indices.u64'))
        row = f'{name}\t{indices.size}\t{digest}\tTrue\t16384\t{overlap}'
        log.write(row + '\n')
        print(row)
print('Recovered sample identities only; residual panels and transform provenance remain required.')
PY
sha256sum AGENTS.md TASK.md research/correlated_pair_allocation/diagnostic.py research/correlated_pair_allocation/extract_stage_panels.cpp research/correlated_pair_allocation/write_indices.py "$out/requested_design.md" > "$out/source_hashes.sha256"
git diff --check
date -Is
