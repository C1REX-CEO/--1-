"""Edge cases for matrix implementations, including malformed files."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import ROOT, save_matrix, load_matrix

def main():
    p=argparse.ArgumentParser()
    p.add_argument('backend',choices=['cuda','mpi'])
    p.add_argument('--exe',required=True)
    p.add_argument('--launcher',default='mpiexec')
    p.add_argument('--work-dir',type=Path)
    p.add_argument('--out',type=Path,help='Save checks without replacing the local verification log')
    args=p.parse_args()
    work=args.work_dir.resolve() if args.work_dir else ROOT/'experiments'/'work'/('check_'+args.backend)
    work.mkdir(parents=True,exist_ok=True)
    ap,bp,cp,sp=[work/name for name in ['A.txt','B.txt','C.txt','stats.csv']]
    def command(config):
        base=[str(Path(args.exe).resolve()),str(ap),str(bp),str(cp),str(sp)]
        return (shlex.split(args.launcher)+['-n',str(config)]+base if args.backend=='mpi'
                else base+list(map(str,config)))
    configs=([1,2,4,8] if args.backend=='mpi' else
             [('naive',8,8),('naive',16,16),('naive',32,8),('tiled',8,8),('tiled',16,16),('tiled',32,32)])
    checks=[]
    for n in [1,2,3,7,17,33]:
        rng=np.random.default_rng(n)
        a=rng.integers(-10,11,(n,n),dtype=np.int64)
        b=rng.integers(-10,11,(n,n),dtype=np.int64)
        save_matrix(ap,a); save_matrix(bp,b)
        for config in configs:
            subprocess.run(command(config),capture_output=True,check=True,timeout=60)
            assert np.array_equal(load_matrix(cp),a@b),(n,config)
            checks.append(dict(n=n,config=config,verified=True))
    for name,contents in [('empty',''),('zero','0\n'),('truncated','2\n1 2\n'),
                          ('extra','1\n2 3\n'),('overflow','1\n9223372036854775807\n'),
                          ('mismatch','2\n1 2\n3 4\n')]:
        ap.write_text(contents,encoding='utf-8'); save_matrix(bp,np.ones((1,1),dtype=np.int64))
        result=subprocess.run(command(configs[-1]),capture_output=True,timeout=60)
        assert result.returncode!=0,name
        checks.append(dict(invalid_input=name,rejected=True))
    target=args.out or ROOT/('lab3_mpi' if args.backend=='mpi' else 'lab4_cuda')/'checks.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print(f'{len(checks)} checks passed')
if __name__=='__main__': main()
