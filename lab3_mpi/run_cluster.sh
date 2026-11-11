#!/usr/bin/env bash
# Run INSIDE a scheduler allocation, not on a login node.
# MPI module must already be loaded. For Korolev use job.pbs.
set -euo pipefail
: "${PBS_JOBID:?Run inside a PBS allocation; submit lab3_mpi/job.pbs}"
: "${PBS_NODEFILE:?PBS node file is missing}"
: "${PBS_NP:?PBS process allocation is missing}"
[[ "$PBS_NP" =~ ^[1-9][0-9]*$ && "$PBS_NP" -ge 8 ]] || {
    echo 'The full experiment needs at least 8 allocated cores' >&2; exit 1;
}
[[ -r "$PBS_NODEFILE" ]] || { echo 'Cannot read PBS_NODEFILE' >&2; exit 1; }
cd "$(dirname "$0")/.."
: "${MPI_LAUNCHER:=bash lab3_mpi/korolev_mpirun.sh}"
: "${RUN_LABEL:=korolev}"
: "${RESULT_DIR:=lab3_mpi/results_korolev}"
: "${PYTHON:=python3}"
: "${MPICXX:=mpicxx}"
: "${CXX:=g++}"
mkdir -p "$RESULT_DIR/build"
RESULT_DIR="$(cd "$RESULT_DIR" && pwd)"
if [[ -e "$RESULT_DIR/raw.csv" || -e "$RESULT_DIR/serial/raw.csv" ]]; then
    echo "Result directory already contains measurements: $RESULT_DIR" >&2
    exit 1
fi
"$PYTHON" -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"; import numpy, matplotlib'
bash lab3_mpi/build_linux.sh "$RESULT_DIR/build" 2>&1 | tee "$RESULT_DIR/build.log"
"$PYTHON" experiments/check.py serial --exe "$RESULT_DIR/build/matrix_serial" \
    --work-dir "$RESULT_DIR/work/check-serial" --out "$RESULT_DIR/checks_serial.json"
"$PYTHON" experiments/check.py mpi --exe "$RESULT_DIR/build/matrix_mpi" --launcher "$MPI_LAUNCHER" \
    --work-dir "$RESULT_DIR/work/check" --out "$RESULT_DIR/checks.json"
"$PYTHON" experiments/run.py serial --exe "$RESULT_DIR/build/matrix_serial" \
    --label "$RUN_LABEL" --out "$RESULT_DIR/serial" \
    --work-dir "$RESULT_DIR/work/serial" --sizes 200 400 800 1200 1600 2000 --repeats 3
"$PYTHON" experiments/run.py mpi --exe "$RESULT_DIR/build/matrix_mpi" \
    --launcher "$MPI_LAUNCHER" --label "$RUN_LABEL" --out "$RESULT_DIR" \
    --work-dir "$RESULT_DIR/work/benchmark" \
    --sizes 200 400 800 1200 1600 2000 --processes 1 2 4 8 --repeats 3
"$PYTHON" experiments/summarize.py mpi --input "$RESULT_DIR" --serial-input "$RESULT_DIR/serial"
