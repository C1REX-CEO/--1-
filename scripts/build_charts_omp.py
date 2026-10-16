import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).parent.resolve()
RESULTS_CSV = SCRIPT_DIR.parent / "results.csv"
FIGURES_DIR = SCRIPT_DIR / "figures_omp"
FIGURES_DIR.mkdir(exist_ok=True)

COLORS = {1: "#2c7fb8", 2: "#d95f02", 4: "#1b9e77", 8: "#7570b3"}


def load_results():
    # data[threads] = [(N, time_ms, gflops), ...]
    data = defaultdict(list)
    with open(RESULTS_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            data[int(row["threads"])].append(
                (int(row["size"]), float(row["time_ms"]), float(row["gflops"]))
            )
    for t in data:
        data[t].sort()
    return data


def plot_time(data, log_scale, filename):
    fig, ax = plt.subplots(figsize=(8, 5))
    for t, rows in sorted(data.items()):
        n = [r[0] for r in rows]
        ms = [r[1] for r in rows]
        ax.plot(n, ms, marker="o", color=COLORS.get(t), label=f"{t} пот.")
    if log_scale:
        ax.set_yscale("log")
        ax.set_title("Время выполнения (логарифмическая шкала)")
    else:
        ax.set_title("Время выполнения от размера матрицы N")
    ax.set_xlabel("N (N x N)")
    ax.set_ylabel("Время, мс")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename)
    plt.close(fig)


def speedup_table(data):
    # speedup[N] = [(threads, S), ...], S = T1 / Tp
    t1 = {r[0]: r[1] for r in data[1]}
    speedup = defaultdict(list)
    for t, rows in sorted(data.items()):
        for n, ms, _ in rows:
            speedup[n].append((t, t1[n] / ms))
    return speedup


def plot_speedup(data, filename):
    speedup = speedup_table(data)
    threads = sorted(data)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(threads, threads, linestyle="--", color="gray", label="идеал (S = p)")
    for n, rows in sorted(speedup.items()):
        ax.plot([r[0] for r in rows], [r[1] for r in rows], marker="o", label=f"N = {n}")
    ax.set_title("Ускорение S = T1 / Tp от числа потоков")
    ax.set_xlabel("Число потоков p")
    ax.set_ylabel("Ускорение S")
    ax.set_xticks(threads)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename)
    plt.close(fig)


def plot_efficiency(data, filename):
    speedup = speedup_table(data)
    threads = sorted(data)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.axhline(1.0, linestyle="--", color="gray", label="идеал (E = 1)")
    for n, rows in sorted(speedup.items()):
        ax.plot([r[0] for r in rows], [r[1] / r[0] for r in rows], marker="o", label=f"N = {n}")
    ax.set_title("Эффективность E = S / p от числа потоков")
    ax.set_xlabel("Число потоков p")
    ax.set_ylabel("Эффективность E")
    ax.set_xticks(threads)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename)
    plt.close(fig)


def plot_gflops(data, filename):
    fig, ax = plt.subplots(figsize=(8, 5))
    for t, rows in sorted(data.items()):
        ax.plot([r[0] for r in rows], [r[2] for r in rows],
                marker="o", color=COLORS.get(t), label=f"{t} пот.")
    ax.set_title("Производительность (GFLOPS) от размера N")
    ax.set_xlabel("N (N x N)")
    ax.set_ylabel("GFLOPS")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename)
    plt.close(fig)


def main():
    if not RESULTS_CSV.exists():
        print(f"нет {RESULTS_CSV}, сначала запусти run_experiments.py")
        return

    data = load_results()

    plot_time(data, log_scale=False, filename="time_by_size.png")
    plot_time(data, log_scale=True, filename="time_by_size_log.png")
    plot_speedup(data, filename="speedup_by_threads.png")
    plot_efficiency(data, filename="efficiency_by_threads.png")
    plot_gflops(data, filename="throughput_by_size.png")

    print("Ускорение S = T1 / Tp:")
    for n, rows in sorted(speedup_table(data).items()):
        print(f"N={n:>5}  " + "  ".join(f"p={t}: S={s:.2f} E={s / t:.2f}" for t, s in rows))

    print(f"графики сохранены в {FIGURES_DIR}")


if __name__ == "__main__":
    main()
