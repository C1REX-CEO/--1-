import random


def generate(n: int, filename: str) -> None:
    with open(filename, "w") as f:
        f.write(f"{n}\n")
        for _ in range(n):
            row = " ".join(str(random.randint(1, 9)) for _ in range(n))
            f.write(row + "\n")


if __name__ == "__main__":
    sizes = [200, 400, 800, 1200, 1600, 2000]
    for size in sizes:
        name_a = f"Matrix(A)_{size}.txt"
        name_b = f"Matrix(B)_{size}.txt"
        generate(size, name_a)
        generate(size, name_b)
        print(f"Созданы {name_a} и {name_b}")