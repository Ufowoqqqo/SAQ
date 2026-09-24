"""Copy only allowed learn/base inputs to local scratch, checking frozen SHA-256."""
import hashlib
from pathlib import Path
import time

root = Path('/rwproject/kdd-db/kluaq')
scratch = Path('/tmp/saq-data-aware-rebuild-20260923/inputs')
scratch.mkdir(parents=True, exist_ok=True)
sources = (
    ('sift_learn.fvecs', root / 'quant-hardness/runs/phase4a_gap_guided_refinement_v1/sift_learn.fvecs',
     '331bc82b6a0e89465776a3ba0c2113e0bd0cceaa014ec3ed639bc8b981af72ea'),
    ('sift_base.fvecs', root / 'dataset/sift1m/hf_download/sift_base.fvecs',
     '21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816'),
    ('gist_base.fvecs', root / 'dataset/gist/gist_base.fvecs',
     '73418110328f5aa522d9f6b0cd9115a6c515dc44e3c48420e506ddeddbdbdbc0'),
)
print('name\tsha256\tsource\tlocal_copy\tbytes\twall_seconds', flush=True)
for name, source, expected in sources:
    started = time.monotonic()
    target = scratch / name
    partial = scratch / (name + '.part')
    digest = hashlib.sha256()
    with source.open('rb') as src, partial.open('wb') as dst:
        for block in iter(lambda: src.read(8 << 20), b''):
            digest.update(block)
            dst.write(block)
    if digest.hexdigest() != expected:
        raise ValueError(f'{name}: frozen official hash mismatch')
    partial.replace(target)
    print(f'{name}\t{digest.hexdigest()}\t{source}\t{target}\t{target.stat().st_size}\t{time.monotonic()-started:.6f}', flush=True)
