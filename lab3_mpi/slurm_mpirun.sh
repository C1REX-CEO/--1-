#!/bin/bash
# Hydra starts its processes through Slurm; do not use SSH to bypass the scheduler.
set -euo pipefail
: "${SLURM_JOB_ID:?Submit lab3_mpi/job.slurm using sbatch}"
: "${SLURM_NTASKS:?Missing Slurm task allocation}"
if [[ $# -lt 3 || "$1" != '-n' || ! "$2" =~ ^[1-9][0-9]*$ ]]; then
    echo 'Usage: slurm_mpirun.sh -n COUNT executable [arguments...]' >&2; exit 2
fi
if [[ ! "$SLURM_NTASKS" =~ ^[1-9][0-9]*$ || "$2" -gt "$SLURM_NTASKS" ]]; then
    echo 'Requested processes exceed allocation' >&2; exit 2
fi
count="$2"
shift 2
export I_MPI_HYDRA_BOOTSTRAP=slurm
exec mpirun -np "$count" "$@"
