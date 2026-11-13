"""Python 3.6+, standard library only. Verify every run against offline NumPy hashes."""
import argparse
import csv
import datetime
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys


def matrix_digest(path):
    digest = hashlib.sha256()
    # Windows C++ writes CRLF; Linux writes LF. Numeric text is otherwise canonical.
    with Path(path).open(encoding='ascii', newline=None) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), ''):
            digest.update(chunk.encode('ascii'))
    return digest.hexdigest()


def verify_matrix(path, expected):
    actual = matrix_digest(path)
    if actual != expected:
        raise ValueError('Matrix differs from independent NumPy reference: ' + str(path))
    return actual


def read_stats(path, n, processes):
    with Path(path).open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError('Expected exactly one statistics row')
    row = rows[0]
    if int(row['n']) != n or int(row['processes']) != processes:
        raise ValueError('Statistics do not match requested N/processes')
    for field in ('total_ms', 'compute_ms', 'gops'):
        value = float(row[field])
        if not math.isfinite(value) or value < 0 or (field == 'total_ms' and value == 0):
            raise ValueError('Invalid statistics: ' + field)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--serial', type=Path, required=True)
    parser.add_argument('--mpi', type=Path, required=True)
    parser.add_argument('--launcher', default='mpirun')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--mode', choices=('smoke', 'full'), default='smoke')
    args = parser.parse_args()
    manifest = json.loads((args.inputs/'inputs.json').read_text(encoding='utf-8'))
    sizes = [1, 3, 17] if args.mode == 'smoke' else [200, 400, 800, 1200, 1600, 2000]
    repeats = 1 if args.mode == 'smoke' else 3
    out = args.out.resolve()
    work = out/'work'
    work.mkdir(parents=True, exist_ok=True)
    (out/'serial').mkdir(exist_ok=True)
    if (out/'raw.csv').exists() or (out/'serial/raw.csv').exists():
        raise ValueError('Existing results must not be overwritten: ' + str(out))
    metadata = dict(label=args.label, mode=args.mode, platform=platform.platform(),
                    hostname=platform.node(), python=sys.version, command=sys.argv,
                    date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    slurm={k: v for k, v in os.environ.items() if k.startswith('SLURM_')},
                    verification='SHA256 of complete canonical output vs offline NumPy reference',
                    input_manifest=manifest, repeats=repeats)
    executables = {'serial': args.serial.resolve(), 'mpi': args.mpi.resolve()}
    for backend, exe in executables.items():
        metadata[backend + '_sha256'] = hashlib.sha256(exe.read_bytes()).hexdigest()
    (out/'environment.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    shutil.copyfile(str(out/'environment.json'), str(out/'serial/environment.json'))
    fields = ['n', 'processes', 'total_ms', 'compute_ms', 'gops', 'repeat', 'label',
              'verified', 'max_abs_error', 'implementation', 'result_sha256']
    # Exclusive creation prevents accidentally replacing earlier measurements.
    with (out/'raw.csv').open('x', newline='') as mf, (out/'serial/raw.csv').open('x', newline='') as sf:
        writers = {'mpi': csv.DictWriter(mf, fieldnames=fields),
                   'serial': csv.DictWriter(sf, fieldnames=fields)}
        for writer in writers.values():
            writer.writeheader()
        for n in sizes:
            reference = manifest['matrices'][str(n)]
            for name in ('A', 'B'):
                path = work/(name + '.txt')
                with gzip.open(str(args.inputs/('{}-{}.txt.gz'.format(n, name))), 'rb') as src, path.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
                verify_matrix(path, reference[name])
            for backend, processes in [('serial', 1)] + [('mpi', p) for p in (1, 2, 4, 8)]:
                for repeat in range(repeats):
                    cp, sp = work/'C.txt', work/'stats.csv'
                    for path in (cp, sp):
                        if path.exists():
                            path.unlink()
                    command = [str(executables[backend])] + [str(work/name) for name in ('A.txt', 'B.txt', 'C.txt', 'stats.csv')]
                    if backend == 'mpi':
                        command = shlex.split(args.launcher) + ['-n', str(processes)] + command
                    log = out/'{}_{}_{}_{}.log'.format(n, backend, processes, repeat)
                    with log.open('w') as stream:
                        # check=True stops immediately on a failed MPI launch.
                        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                       check=True, timeout=900)
                    digest = verify_matrix(cp, reference['C'])
                    row = read_stats(sp, n, processes)
                    row.update(repeat=repeat, label=args.label, verified=True, max_abs_error=0,
                               implementation=backend, result_sha256=digest)
                    writers[backend].writerow(row)
                    mf.flush(); sf.flush()
                    print('N={} {} p={} repeat={}: verified, {} ms'.format(
                        n, backend, processes, repeat + 1, row['total_ms']), flush=True)
    (out/'SUCCESS.txt').write_text('All {} measurements verified.\n'.format(len(sizes)*5*repeats))
    print('SUCCESS: ' + str(out), flush=True)


if __name__ == '__main__':
    main()
