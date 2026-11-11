"""Reproducible, verified serial/MPI/CUDA experiments."""
import argparse
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def save_matrix(path, data):
    np.savetxt(path, data, fmt='%d', header=str(len(data)), comments='')

def load_matrix(path):
    with open(path, encoding='utf-8') as f:
        n = int(f.readline())
        data = np.loadtxt(f, dtype=np.int64, ndmin=2)
    if data.shape != (n, n):
        raise ValueError(f'Incorrect result shape {data.shape}, expected {(n,n)}')
    return data

def reference(a, b):
    # Integers in [-10,10], N<=46340: every partial sum is exactly representable
    # in float64 (absolute sum <= N*100 << 2**53). BLAS gives an exact reference.
    return (a.astype(np.float64) @ b.astype(np.float64)).astype(np.int64)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('backend', choices=['mpi', 'cuda', 'serial'])
    p.add_argument('--exe', required=True)
    p.add_argument('--sizes', nargs='+', type=int, default=[200,400,800,1200,1600,2000])
    p.add_argument('--processes', nargs='+', type=int, default=[1,2,4,8])
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--launcher', default='mpiexec', help='e.g. "mpiexec --bind-to core" or "srun --cpu-bind=cores"')
    p.add_argument('--label', required=True, help='Machine/run label, e.g. local-rtx3060 or korolev')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--work-dir', type=Path, help='Separate temporary directory for a cluster job')
    args = p.parse_args()
    if args.repeats < 1 or any(n < 1 or n > 46340 for n in args.sizes) or any(n < 1 for n in args.processes):
        p.error('Invalid sizes/processes/repeats')
    exe = str(Path(args.exe).resolve())
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = args.work_dir.resolve() if args.work_dir else ROOT/'experiments'/'work'/args.backend
    work.mkdir(parents=True, exist_ok=True)
    metadata = dict(label=args.label, platform=platform.platform(), hostname=platform.node(), cpu=platform.processor(),
                    logical_cpus=os.cpu_count(), python=sys.version, numpy=np.__version__,
                    date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    command=sys.argv, executable_sha256=hashlib.sha256(Path(exe).read_bytes()).hexdigest(),
                    repeats=args.repeats, seed=42, backend=args.backend)
    try:
        metadata['gpu'] = subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'],text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    (out/'environment.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    configs = ([('serial', 1, 0)] if args.backend == 'serial' else
               [('mpi', count, 0) for count in args.processes] if args.backend == 'mpi' else
               [('naive',8,8),('naive',16,16),('naive',32,8),('tiled',8,8),('tiled',16,16),('tiled',32,32)])
    with (out/'raw.csv').open('w',newline='',encoding='utf-8') as output:
        writer = None
        for n in args.sizes:
            rng = np.random.default_rng(42+n)
            a = rng.integers(-10,11,size=(n,n),dtype=np.int64)
            b = rng.integers(-10,11,size=(n,n),dtype=np.int64)
            expected = reference(a,b)
            ap,bp,cp,sp = [work/name for name in ('A.txt','B.txt','C.txt','stats.csv')]
            save_matrix(ap,a); save_matrix(bp,b)
            for kind,x,y in configs:
                for repeat in range(args.repeats):
                    command = [exe,str(ap),str(bp),str(cp),str(sp)]
                    if args.backend == 'mpi': command = shlex.split(args.launcher)+['-n',str(x)]+command
                    elif args.backend == 'cuda': command += [kind,str(x),str(y)]
                    cp.unlink(missing_ok=True); sp.unlink(missing_ok=True)
                    run = subprocess.run(command,text=True,capture_output=True,timeout=900)
                    (out/f'{n}_{kind}_{x}_{y}_{repeat}.log').write_text(run.stdout+run.stderr,encoding='utf-8')
                    if run.returncode: raise RuntimeError(f'{command}\n{run.stdout}\n{run.stderr}')
                    actual = load_matrix(cp)
                    if not np.array_equal(actual,expected): raise AssertionError(f'Incorrect output N={n}, config={kind,x,y}')
                    with sp.open(encoding='utf-8') as f: row = next(csv.DictReader(f))
                    row.update(repeat=repeat,label=args.label,verified=True,max_abs_error=0,implementation=args.backend)
                    if writer is None:
                        writer = csv.DictWriter(output,fieldnames=list(row)); writer.writeheader()
                    writer.writerow(row); output.flush()
                    print(f'N={n}, {kind} {x}x{y}, repeat={repeat+1}: verified; total={row["total_ms"]} ms',flush=True)

if __name__ == '__main__': main()
