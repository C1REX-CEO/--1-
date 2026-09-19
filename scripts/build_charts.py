import csv
from pathlib import Path

import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).parent.resolve()
RESULTS_CSV = SCRIPT_DIR / "results.csv"
FIGURES_DIR = SCRIPT_DIR / "figures"
FIGURES_DIR.mkdir(exist_ok=True)


def load_results():
    n, t_ms, gflops = [], [], []
    with open(RESULTS_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n.append(int(row["N"]))
            t_ms.append(float(row["Time_ms"]))
            gflops.append(float(row["GFLOPS"]))
    return n, t_ms, gflops


def plot_time(n, t_ms, log_scale, filename):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(n, t_ms, marker="o", color="#2c7fb8")
    if log_scale:
        ax.set_yscale("log")
        ax.set_title("Время выполнения (логарифмическая шкала)")
    else:
        ax.set_title("Время выполнения от размера матрицы N")
    ax.set_xlabel("N (N x N)")
    ax.set_ylabel("Время, мс")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename)
    plt.close(fig)


def plot_gflops(n, gflops, filename):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(n, gflops, marker="o", color="#d95f02")
    ax.set_title("Производительность (GFLOPS) от размера N")
    ax.set_xlabel("N (N x N)")
    ax.set_ylabel("GFLOPS")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename)
    plt.close(fig)


def main():
    if not RESULTS_CSV.exists():
        print(f"нет {RESULTS_CSV}, сначала запусти benchmark.py")
        return

    n, t_ms, gflops = load_results()

    plot_time(n, t_ms, log_scale=False, filename="time_by_size.png")
    plot_time(n, t_ms, log_scale=True, filename="time_by_size_log.png")
    plot_gflops(n, gflops, filename="throughput_by_size.png")

    print(f"графики сохранены в {FIGURES_DIR}")


if __name__ == "__main__":
    main()
