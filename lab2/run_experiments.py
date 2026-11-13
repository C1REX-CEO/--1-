import subprocess
import csv
import time
import os


def run_one(size: int, threads: int) -> dict:
    a = f"Matrix(A)_{size}.txt"
    b = f"Matrix(B)_{size}.txt"
    stats = f"stats_{size}_T{threads}.txt"

    if os.path.exists(stats):
        os.remove(stats)

    proc = subprocess.Popen(
        ["matrix_omp.exe", a, b, "RESULT.txt", stats, str(threads)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"  !! таймаут 30s, процесс убит")

    time.sleep(0.5)

    if not os.path.exists(stats):
        print(f"  !! файл {stats} не создан")
        return {"size": size, "threads": threads, "time_ms": 0.0, "gflops": 0.0}

    with open(stats, "r", encoding="utf-8") as f:
        text = f.read()

    time_ms = 0.0
    gflops = 0.0
    for line in text.splitlines():
        if "Время выполнения:" in line:
            time_ms = float(line.split(":")[1].replace("ms", "").strip())
        if "Производительность:" in line:
            gflops = float(line.split(":")[1].replace("GFLOPS", "").strip())

    return {"size": size, "threads": threads, "time_ms": time_ms, "gflops": gflops}


if __name__ == "__main__":
    sizes = [200, 400, 800, 1200, 1600, 2000]
    threads_list = [1, 2, 4, 8]

    results = []
    for size in sizes:
        for t in threads_list:
            print(f"Запуск: N={size}, потоков={t}", flush=True)
            r = run_one(size, t)
            results.append(r)
            print(f"  -> time={r['time_ms']:.2f} ms, GFLOPS={r['gflops']:.4f}", flush=True)

    with open("results.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["size", "threads", "time_ms", "gflops"])
        writer.writeheader()
        writer.writerows(results)

    print()
    print("=" * 60)
    print("ИТОГИ:")
    print("=" * 60)
    for r in results:
        print(f"N={r['size']:>5}  T={r['threads']:>2}  "
              f"time={r['time_ms']:>10.2f} ms  GFLOPS={r['gflops']:>8.4f}")

    print()
    print("Результаты сохранены в results.csv")