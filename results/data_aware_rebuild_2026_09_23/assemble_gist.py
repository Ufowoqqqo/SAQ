"""Verify disjoint official archive ranges, then extract only frozen learn."""
import hashlib
import os
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRATCH = Path('/tmp/saq-data-aware-rebuild-20260923')
ARCHIVE_HASH = '01469a7f1c3768853525e543d537e2dfa1adece927616405e360952e3f67df73'
LEARN_HASH = '9b864d69993ffea89f8547c0a1f993727c39152ee040fb48b6de28f5c986ed17'
prefix = SCRATCH / 'gist.tar.gz.part'
assert prefix.stat().st_size == 849494016
pieces = [prefix] + [SCRATCH / f'gist_segment_{i}.part' for i in range(4)]
assert all(p.stat().st_size == 472669667 for p in pieces[1:])
archive = SCRATCH / 'gist.tar.gz'
assert not archive.exists()
digest = hashlib.sha256()
with archive.open('xb') as target:
    for part in pieces:
        with part.open('rb') as source:
            for block in iter(lambda: source.read(1 << 20), b''):
                digest.update(block)
                target.write(block)
    target.flush()
    os.fsync(target.fileno())
assert archive.stat().st_size == 2740172684
assert digest.hexdigest() == ARCHIVE_HASH, digest.hexdigest()
print(f'PASS official archive {digest.hexdigest()}', flush=True)
learn = SCRATCH / 'inputs/gist_learn.fvecs'
assert not learn.exists()
digest = hashlib.sha256()
with tarfile.open(archive, 'r|gz') as source:
    for member in source:
        if member.name != 'gist/gist_learn.fvecs':
            continue
        assert member.isfile() and member.size == 1922000000
        with source.extractfile(member) as data, learn.open('xb') as target:
            for block in iter(lambda: data.read(1 << 20), b''):
                digest.update(block)
                target.write(block)
            target.flush()
            os.fsync(target.fileno())
        break
    else:
        raise RuntimeError('official learn member absent')
assert learn.stat().st_size == 1922000000
assert digest.hexdigest() == LEARN_HASH, digest.hexdigest()
print(f'PASS GIST learn {digest.hexdigest()}', flush=True)
with (ROOT / 'gist_input_verification.tsv').open('w') as target:
    target.write('kind\tpath\tbytes\tsha256\n')
    target.write(f'official_archive\t{archive}\t2740172684\t{ARCHIVE_HASH}\n')
    target.write(f'official_learn\t{learn}\t1922000000\t{LEARN_HASH}\n')
