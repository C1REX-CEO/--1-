#include <chrono>
#include <iostream>
#include "common/matrix.hpp"

// Separate sequential baseline: no MPI initialization, OpenMP or worker threads.
int main(int argc, char** argv) {
    try {
        if (argc != 5) throw std::runtime_error("Usage: matrix_serial A.txt B.txt C.txt stats.csv");
        const Matrix a = read_matrix(argv[1]), b = read_matrix(argv[2]);
        if (a.n != b.n) throw std::runtime_error("Matrix dimensions differ");
        const int n = a.n;
        Matrix c{n, std::vector<long long>(a.data.size(), 0)};
        const auto start = std::chrono::steady_clock::now();
        multiply_rows(a.data.data(), b.data.data(), c.data.data(), n, n);
        const double seconds = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - start).count();
        write_matrix(argv[3], c);
        std::ofstream out(argv[4]);
        out << "n,processes,total_ms,compute_ms,gops\n" << std::setprecision(12)
            << n << ",1," << seconds*1000 << ',' << seconds*1000 << ','
            << (seconds > 0 ? 2.0*n*n*n/seconds/1e9 : 0) << '\n';
        out.close();
        if (!out) throw std::runtime_error("Cannot write statistics");
        std::cout << "Serial N=" << n << " compute_ms=" << seconds*1000 << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
