#!/usr/bin/env bash
# Compile both programs using the compiler/MPI modules chosen for this cluster.
set -euo pipefail
cd "$(dirname "$0")/.."
output="${1:-build}"
mkdir -p "$output"
"${CXX:-g++}" -O2 -std=c++17 lab3_mpi/serial.cpp -o "$output/matrix_serial"
"${MPICXX:-mpicxx}" -O2 -std=c++17 lab3_mpi/main.cpp -o "$output/matrix_mpi"
