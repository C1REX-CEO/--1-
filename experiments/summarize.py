"""Build median tables and figures from measured CSV files only."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser()
    p.add_argument('backend',choices=['mpi','cuda','simd'])
    p.add_argument('--input',type=Path,required=True)
    args=p.parse_args()
    folder=args.input
    if args.backend=='simd':
        with (folder/'results.csv').open() as f: rows=list(csv.DictReader(f))
        widths=[int(r['width']) for r in rows]
        for metric,ylabel,name in [('utilization_pct','Активные полосы, %','utilization'),
                                    ('instructions','Векторные инструкции','instructions')]:
            fig,ax=plt.subplots(figsize=(8,5))
            ax.plot(widths,[float(r[metric]) for r in rows],'o-')
            ax.set(xlabel='Ширина вектора',ylabel=ylabel,xticks=widths)
            ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(folder/(name+'.png'),dpi=160); plt.close(fig)
        text='| Ширина | Инструкции | Активные полосы | Всего полос | Загрузка, % |\n|---:|---:|---:|---:|---:|\n'
        for r in rows:
            text+=f'| {r["width"]} | {r["instructions"]} | {r["utilized_lanes"]} | {r["total_lanes"]} | {float(r["utilization_pct"]):.2f} |\n'
        (folder/'tables.md').write_text(text,encoding='utf-8')
        return
    with (folder/'raw.csv').open() as f: raw=list(csv.DictReader(f))
    groups=defaultdict(list)
    for row in raw:
        if row['verified']!='True': raise ValueError('Unverified row')
        config=(row['processes'] if args.backend=='mpi' else f'{row["kernel"]} {row["block_x"]}x{row["block_y"]}')
        groups[int(row['n']),config].append(row)
    timings=['total_ms','compute_ms'] if args.backend=='mpi' else ['total_ms','kernel_ms']
    summary=[]
    for (n,config),items in sorted(groups.items()):
        row=dict(n=n,config=config,repeats=len(items))
        for metric in timings+['gops']:
            values=[float(r[metric]) for r in items]
            row[metric]=median(values)
            row[metric+'_min']=min(values); row[metric+'_max']=max(values)
        summary.append(row)
    if args.backend=='mpi':
        baseline={r['n']:r['total_ms'] for r in summary if r['config']=='1'}
        for r in summary:
            r['speedup']=baseline[r['n']]/r['total_ms']; r['efficiency']=r['speedup']/int(r['config'])
    with (folder/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0])); writer.writeheader(); writer.writerows(summary)
    configs=sorted({r['config'] for r in summary})
    table=''
    for metric in timings:
        table+=f'### {metric}: медиана, мс\n\n| N | '+' | '.join(configs)+' |\n|---:|'+':---:|'*len(configs)+'\n'
        for n in sorted({r['n'] for r in summary}):
            values={r['config']:r[metric] for r in summary if r['n']==n}
            table+=f'| {n} | '+' | '.join(f'{values[c]:.4f}' if c in values else '—' for c in configs)+' |\n'
        table+='\n'
        fig,ax=plt.subplots(figsize=(9,5))
        for config in configs:
            data=[r for r in summary if r['config']==config]
            ax.plot([r['n'] for r in data],[r[metric] for r in data],'o-',label=config)
        ax.set(xlabel='Размер матрицы N',ylabel='Время, мс',title=metric)
        ax.grid(alpha=.3); ax.legend(); fig.tight_layout(); fig.savefig(folder/(metric+'.png'),dpi=160); plt.close(fig)
    if args.backend=='mpi':
        for metric,ylabel in [('speedup','Ускорение T1/Tp'),('efficiency','Эффективность S/p')]:
            fig,ax=plt.subplots(figsize=(8,5))
            for n in sorted({r['n'] for r in summary}):
                data=sorted([r for r in summary if r['n']==n],key=lambda r:int(r['config']))
                ax.plot([int(r['config']) for r in data],[r[metric] for r in data],'o-',label=f'N={n}')
            ax.set(xlabel='Число процессов',ylabel=ylabel); ax.grid(alpha=.3); ax.legend()
            fig.tight_layout(); fig.savefig(folder/(metric+'.png'),dpi=160); plt.close(fig)
    (folder/'tables.md').write_text(table,encoding='utf-8')
    print(f'Summary and figures written to {folder}')
if __name__=='__main__': main()
