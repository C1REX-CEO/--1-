"""Run locally with NumPy: package sources and reproducible inputs for Python 3.6."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'build/deploy-slurm/lab3-upload'
FILES = ['common/matrix.hpp', 'lab3_mpi/main.cpp', 'lab3_mpi/serial.cpp',
         'lab3_mpi/build_linux.sh', 'lab3_mpi/job.slurm', 'lab3_mpi/slurm_mpirun.sh',
         'lab3_mpi/run_portable.py', 'lab3_mpi/START_HERE.md', 'lab3_mpi/SLURM.md']


def matrix_bytes(array):
    stream = io.StringIO()
    np.savetxt(stream, array, fmt='%d', header=str(len(array)), comments='')
    return stream.getvalue().encode('ascii')


def main():
    (DEST/'inputs').mkdir(parents=True, exist_ok=True)
    packaged = []
    for name in FILES:
        path = DEST/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT/name).read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8'))
        packaged.append(name)
    manifest = dict(numpy=np.__version__, seed='42+N', range=[-10, 10],
                    reference='NumPy float64 matmul converted to int64; exact for these bounded integers',
                    matrices={})
    for n in [1, 3, 17, 200, 400, 800, 1200, 1600, 2000]:
        rng = np.random.default_rng(42+n)
        a = rng.integers(-10, 11, size=(n, n), dtype=np.int64)
        b = rng.integers(-10, 11, size=(n, n), dtype=np.int64)
        c = (a.astype(np.float64) @ b.astype(np.float64)).astype(np.int64)
        # Each partial sum is bounded by 100*N << 2**53. No roundoff in this reference.
        if n <= 200:
            np.testing.assert_array_equal(c, a @ b)
        hashes = {}
        for name, array in [('A', a), ('B', b), ('C', c)]:
            data = matrix_bytes(array)
            hashes[name] = hashlib.sha256(data).hexdigest()
            if name != 'C':
                filename = 'inputs/{}-{}.txt.gz'.format(n, name)
                # Store inputs only. All outputs are checked against the complete reference hash.
                (DEST/filename).write_bytes(gzip.compress(data, compresslevel=6, mtime=0))
                packaged.append(filename)
        manifest['matrices'][str(n)] = hashes
        print('Prepared N={}'.format(n), flush=True)
    (DEST/'inputs/inputs.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    packaged.append('inputs/inputs.json')
    hashes = {name: hashlib.sha256((DEST/name).read_bytes()).hexdigest() for name in packaged}
    (DEST/'manifest.json').write_text(json.dumps(hashes, indent=2)+'\n', encoding='utf-8')
    archive_path = ROOT/'build/lab3-slurm-upload.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in packaged + ['manifest.json']:
            archive.write(DEST/name, 'lab3-upload/'+name)
    print('Folder: ' + str(DEST))
    print('Archive: {} ({:.1f} MiB)'.format(archive_path, archive_path.stat().st_size/2**20))


if __name__ == '__main__':
    main()
