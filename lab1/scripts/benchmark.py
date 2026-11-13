import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent.resolve()
EXE = ROOT / "matrix.exe"
RESULTS_CSV = ROOT / "scripts" / "results.csv"
TMP_DIR = ROOT / "scripts" / "bench_data"

SIZES = [10, 50, 100, 200, 300, 400, 600, 800]
SEED = 42
VAL_MIN, VAL_MAX = -10, 10

STAT_PATTERNS = {
    "time_ms": re.compile(r"Время выполнения\s*:\s*([\d.]+)"),
    "operations": re.compile(r"Объем задачи \(операций\)\s*:\s*(\d+)"),
    "gflops": re.compile(r"Производительность\s*:\s*([\d.]+)"),
}


def save_matrix(path: Path, m: np.ndarray) -> None:
    with open(path, "w", encoding="ascii") as f:
        f.write(f"{m.shape[0]}\n")
        np.savetxt(f, m, fmt="%d")


def load_matrix(path: Path) -> np.ndarray:
    with open(path, "r", encoding="ascii") as f:
        data = f.read().split()
    n = int(data[0])
    return np.array(data[1:], dtype=np.int64).reshape(n, n)


def read_stats(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


def parse_stats(text: str) -> dict:
    out = {}
    for key, rx in STAT_PATTERNS.items():
        m = rx.search(text)
        if not m:
            raise RuntimeError(f"поле '{key}' не найдено в статистике")
        out[key] = float(m.group(1))
    return out


def run_one(n: int, rng: np.random.Generator) -> tuple:
    A = rng.integers(VAL_MIN, VAL_MAX + 1, size=(n, n))
    B = rng.integers(VAL_MIN, VAL_MAX + 1, size=(n, n))

    fa, fb = TMP_DIR / "A.txt", TMP_DIR / "B.txt"
    fc, fs = TMP_DIR / "C.txt", TMP_DIR / "stats.txt"
    save_matrix(fa, A)
    save_matrix(fb, B)

    res = subprocess.run(
        [str(EXE), str(fa), str(fb), str(fc), str(fs)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if res.returncode != 0:
        raise RuntimeError(res.stderr)

    stats = parse_stats(read_stats(fs))
    max_diff = int(np.abs(load_matrix(fc) - (A @ B)).max())
    return stats, max_diff


def main() -> None:
    if not EXE.exists():
        sys.exit(f"нет {EXE}, собери: g++ -O2 -std=c++17 main.cpp -o matrix.exe")

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rows = []

    print(f"{'N':>6} {'Время, мс':>12} {'GFLOPS':>8} {'MaxDiff':>8}  Статус")
    for n in SIZES:
        try:
            stats, max_diff = run_one(n, rng)
        except RuntimeError as e:
            print(f"{n:6d}  ошибка: {e}")
            continue

        status = "OK" if max_diff == 0 else "FAIL"
        print(f"{n:6d} {stats['time_ms']:12.4f} {stats['gflops']:8.4f} {max_diff:8d}  {status}")
        rows.append((n, stats["time_ms"], int(stats["operations"]), stats["gflops"], max_diff, status))

    RESULTS_CSV.parent.mkdir(exist_ok=True)
    with open(RESULTS_CSV, "w", encoding="utf-8") as f:
        f.write("N,Time_ms,Operations,GFLOPS,MaxDiff,Status\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    print(f"\nсохранено: {RESULTS_CSV}")


if __name__ == "__main__":
    main()
