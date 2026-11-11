import argparse
import csv
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--pattern',default=str(ROOT/'build'/'myexp_{width}.exe'))
    args=p.parse_args()
    out=ROOT/'lab5_simd'/'results'
    out.mkdir(exist_ok=True)
    checks=[]
    with (out/'results.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['width','n','instructions','utilized_lanes','total_lanes','utilization_pct'])
        writer.writeheader()
        for width in [1,2,3,4,8,16]:
            for n in sorted(set([1,3,width,width+1,2*width-1,2*width,10000])):
                run=subprocess.run([args.pattern.format(width=width),'-s',str(n)],capture_output=True,text=True,check=True)
                assert 'Failed' not in run.stdout and 'Results matched' in run.stdout
                (out/f'w{width}_n{n}.log').write_text(run.stdout,encoding='utf-8')
                checks.append(dict(width=width,n=n,passed=True))
                if n==10000 and width in [2,4,8,16]:
                    def integer(label): return int(re.search(re.escape(label)+r'\s*(\d+)',run.stdout)[1])
                    used,total=integer('Utilized Vector Lanes:'),integer('Total Vector Lanes:')
                    writer.writerow(dict(width=width,n=n,instructions=integer('Total Vector Instructions:'),
                                         utilized_lanes=used,total_lanes=total,utilization_pct=100*used/total))
    (out/'checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print(f'{len(checks)} SIMD checks passed')
if __name__=='__main__': main()
