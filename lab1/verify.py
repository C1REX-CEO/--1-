import sys

import numpy as np


def load_matrix(filename: str) -> np.ndarray:
    with open(filename, "r", encoding="utf-8") as f:
        data = f.read().split()
    n = int(data[0])
    return np.array(data[1:], dtype=np.int64).reshape(n, n)


def main() -> None:
    file_a = sys.argv[1] if len(sys.argv) > 1 else "Matrix(A).txt"
    file_b = sys.argv[2] if len(sys.argv) > 2 else "Matrix(B).txt"
    file_c = sys.argv[3] if len(sys.argv) > 3 else "RESULT.txt"

    A = load_matrix(file_a)
    B = load_matrix(file_b)
    C_cpp = load_matrix(file_c)
    C_ref = A @ B

    print("A:\n", A)
    print("\nB:\n", B)
    print("\nC++ result:\n", C_cpp)
    print("\nNumPy result:\n", C_ref)

    ok = np.array_equal(C_cpp, C_ref)
    if ok:
        print("\nOK - Results match!")
    else:
        diff = np.abs(C_cpp - C_ref)
        print(f"\nERROR - Results differ! Max abs diff: {diff.max()}")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
