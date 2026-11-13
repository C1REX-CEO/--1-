#include <mpi.h>
#include <iostream>
#include "common/matrix.hpp"

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank, processes;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &processes);
    try {
        if (argc != 5) throw std::runtime_error("Usage: matrix_mpi A.txt B.txt C.txt stats.csv");
        Matrix a, b, c;
        int ok = 1, n = 0;
        if (rank == 0) {
            try {
                a = read_matrix(argv[1]); b = read_matrix(argv[2]);
                if (a.n != b.n) throw std::runtime_error("Matrix dimensions differ");
                n = a.n;
                c = Matrix{n, std::vector<long long>(static_cast<size_t>(n)*n)};
            } catch (const std::exception& e) { std::cerr << e.what() << '\n'; ok = 0; }
        }
        MPI_Bcast(&ok, 1, MPI_INT, 0, MPI_COMM_WORLD);
        if (!ok) { MPI_Finalize(); return 1; }
        MPI_Bcast(&n, 1, MPI_INT, 0, MPI_COMM_WORLD);
        std::vector<int> counts(processes), offsets(processes);
        int offset = 0;
        for (int p = 0; p < processes; ++p) {
            counts[p] = (n/processes + (p < n%processes ? 1 : 0))*n;
            offsets[p] = offset;
            offset += counts[p];
        }
        // Allocate at least one element: valid pointer also for zero-row ranks.
        std::vector<long long> local_a(std::max(1, counts[rank]));
        std::vector<long long> local_c(std::max(1, counts[rank]), 0);
        if (rank != 0) b = Matrix{n, std::vector<long long>(static_cast<size_t>(n)*n)};
        MPI_Barrier(MPI_COMM_WORLD);
        const double start = MPI_Wtime();
        MPI_Bcast(b.data.data(), n*n, MPI_LONG_LONG_INT, 0, MPI_COMM_WORLD);
        MPI_Scatterv(a.data.data(), counts.data(), offsets.data(), MPI_LONG_LONG_INT,
                     local_a.data(), counts[rank], MPI_LONG_LONG_INT, 0, MPI_COMM_WORLD);
        const double compute_start = MPI_Wtime();
        multiply_rows(local_a.data(), b.data.data(), local_c.data(), counts[rank]/n, n);
        const double compute = MPI_Wtime() - compute_start;
        MPI_Gatherv(local_c.data(), counts[rank], MPI_LONG_LONG_INT,
                    c.data.data(), counts.data(), offsets.data(), MPI_LONG_LONG_INT, 0, MPI_COMM_WORLD);
        const double total = MPI_Wtime() - start;
        double max_compute, max_total;
        MPI_Reduce(&compute, &max_compute, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
        MPI_Reduce(&total, &max_total, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
        if (rank == 0) {
            write_matrix(argv[3], c);
            std::ofstream out(argv[4]);
            out << "n,processes,total_ms,compute_ms,gops\n" << std::setprecision(12)
                << n << ',' << processes << ',' << max_total*1000 << ',' << max_compute*1000
                << ',' << 2.0*n*n*n/max_total/1e9 << '\n';
            out.close();
            if (!out) throw std::runtime_error("Cannot write statistics");
            std::cout << "N=" << n << " processes=" << processes << " total_ms=" << max_total*1000 << '\n';
        }
        MPI_Finalize();
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Rank " << rank << ": " << e.what() << '\n';
        MPI_Abort(MPI_COMM_WORLD, 1);
        return 1;
    }
}
