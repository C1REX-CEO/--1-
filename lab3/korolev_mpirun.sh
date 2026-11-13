#!/usr/bin/env bash
# Intel MPI launcher syntax from https://hpc.ssau.ru/node/36
# Adapter for the Python runner's: launcher -n COUNT executable arguments...
set -euo pipefail
: "${PBS_JOBID:?Run through qsub, inside a PBS job}"
: "${PBS_NODEFILE:?PBS node file is missing}"
: "${PBS_NP:?PBS process allocation is missing}"
if [[ $# -lt 3 || "$1" != '-n' || ! "$2" =~ ^[1-9][0-9]*$ ]]; then
    echo 'Usage: korolev_mpirun.sh -n COUNT executable [arguments...]' >&2
    exit 2
fi
if [[ ! "$PBS_NP" =~ ^[1-9][0-9]*$ || "$2" -gt "$PBS_NP" ]]; then
    echo 'Requested processes exceed the PBS allocation' >&2
    exit 2
fi
[[ -r "$PBS_NODEFILE" ]] || { echo 'Cannot read PBS_NODEFILE' >&2; exit 2; }
count="$2"
shift 2
exec mpirun -r ssh -machinefile "$PBS_NODEFILE" -np "$count" "$@"
