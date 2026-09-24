"""Read-only, bounded filename inventory; hash only the permitted SIFT base."""
import hashlib
import os
from pathlib import Path
import time

root = Path('/rwproject/kdd-db/kluaq')
roots = [
    Path('/tmp/correlated-pair-allocation'),
    Path('/tmp/saq-correlated-pair-allocation'),
    Path('/tmp/saq-structured-2d-modeling'),
    root / 'archive/projects/ann/saq',
    root / 'dataset', root / 'resources', root / 'worktrees',
    root / '.cache/huggingface', root / '.codex/worktrees',
]
names = {
    'residual_nlist1024.fvecs', 'residual_nlist1024_full.fvecs',
    'pca.faiss', 'coarse.faiss', 'base_assignments.u32', 'base_pca.fvecs',
    'STAGE_SOURCE.txt', 'sift_learn.fvecs', 'gist_learn.fvecs',
    'sift_indices.u64', 'gist_indices.u64',
}
print('time=' + time.strftime('%Y-%m-%dT%H:%M:%S%z'), flush=True)
print('Filename inventory only; no query, ground truth or serialized ANN index content read.', flush=True)
for directory in roots:
    count = 0
    matches = []
    errors = []
    for current, subdirs, files in os.walk(directory, followlinks=False, onerror=errors.append):
        subdirs[:] = sorted(d for d in subdirs if d not in {'.git', 'node_modules', '__pycache__'})
        count += len(files)
        for name in sorted(set(files) & names):
            path = Path(current) / name
            matches.append(f'{path}\t{path.stat().st_size} bytes')
    print(f'ROOT\t{directory}\texists={directory.exists()}\tfiles={count}\terrors={len(errors)}', flush=True)
    for error in errors:
        print('ERROR\t' + str(error), flush=True)
    for match in matches:
        print('MATCH\t' + match, flush=True)
base = root / 'dataset/sift1m/hf_download/sift_base.fvecs'
digest = hashlib.sha256()
with base.open('rb') as source:
    for chunk in iter(lambda: source.read(1024 * 1024), b''):
        digest.update(chunk)
expected = '21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816'
assert base.stat().st_size == 516000000 and digest.hexdigest() == expected
print(f'SIFT_OFFICIAL_BASE\t{base}\t{base.stat().st_size}\t{digest.hexdigest()}\tPASS', flush=True)
print('time=' + time.strftime('%Y-%m-%dT%H:%M:%S%z'), flush=True)
