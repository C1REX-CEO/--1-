#!/bin/bash
# Compile on the login node: compute nodes may lack GCC's development headers.
set -eo pipefail
[[ -z "${SLURM_JOB_ID:-}" ]] || { echo 'Run this script on the login node, outside Slurm'; exit 2; }
mode="${1:-smoke}"
case "$mode" in
    smoke) limit=00:10:00 ;;
    full) limit=01:00:00 ;;
    *) echo 'Usage: bash lab3_mpi/submit_slurm.sh smoke|full' >&2; exit 2 ;;
esac
cd "$(dirname "$0")/.."
if ! type module >/dev/null 2>&1; then
    [[ ! -r /etc/profile.d/modules.sh ]] || source /etc/profile.d/modules.sh
fi
module load intel/icc18 intel/mpi5
export CXX=icpc MPICXX=mpiicpc CXX_STANDARD=c++14
set -u
mkdir -p build
# A queued job retains its own build even if another submission happens later.
build_dir="$(mktemp -d "$PWD/build/korolev.XXXXXXXX")"
{
    date -u
    hostname
    (set +u; module list) 2>&1
    icpc --version
    g++ --version
    mpiicpc -show
    printf 'CXX=%s MPICXX=%s FLAGS=-O2 -std=%s\n' "$CXX" "$MPICXX" "$CXX_STANDARD"
} > "$build_dir/build_environment.txt" 2>&1
sha256sum common/matrix.hpp lab3_mpi/main.cpp lab3_mpi/serial.cpp \
    lab3_mpi/build_linux.sh > "$build_dir/sources.sha256"
bash lab3_mpi/build_linux.sh "$build_dir" 2>&1 | tee "$build_dir/build.log"
(cd "$build_dir" && sha256sum matrix_serial matrix_mpi > binaries.sha256)
printf 'BUILD_OK: %s\n' "$build_dir"
sbatch --export="ALL,LAB3_BUILD_DIR=$build_dir" --time="$limit" lab3_mpi/job.slurm "$mode"
