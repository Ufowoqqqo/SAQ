import hashlib
from pathlib import Path
import time

root = Path(__file__).resolve().parent
source = root / 'inputs/gist_learn.fvecs'
expected = '9b864d69993ffea89f8547c0a1f993727c39152ee040fb48b6de28f5c986ed17'
digest, read, started = hashlib.sha256(), 0, time.monotonic()
assert source.stat().st_size == 1922000000
with source.open('rb') as data:
    for block in iter(lambda: data.read(8 << 20), b''):
        digest.update(block)
        read += len(block)
        if read % (128 << 20) == 0:
            print(f'read_bytes={read} wall_seconds={time.monotonic()-started:.2f}', flush=True)
assert digest.hexdigest() == expected, digest.hexdigest()
(root / 'gist_learn_persistent.sha256').write_text(f'{expected}  {source}\n')
print(f'PASS {read} bytes {expected}', flush=True)
