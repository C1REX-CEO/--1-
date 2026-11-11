#!/bin/bash
#SBATCH --job-name=lab3
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=lab3-%j.out
#SBATCH --error=lab3-%j.err

# Submit from lab3-upload: sbatch lab3_mpi/job.slurm smoke (then full after success).
set -eo pipefail
: "${SLURM_JOB_ID:?Use sbatch, not bash, to start this script}"
: "${SLURM_SUBMIT_DIR:?Missing submission directory}"
cd "$SLURM_SUBMIT_DIR"
mode="${1:-smoke}"
[[ "$mode" == smoke || "$mode" == full ]] || { echo 'Expected smoke or full'; exit 2; }
[[ "${SLURM_JOB_NUM_NODES:-0}" == 1 && "${SLURM_NTASKS:-0}" == 8 ]] || {
    echo 'This experiment requires one node with eight task slots'; exit 2;
}
if ! type module >/dev/null 2>&1; then
    [[ ! -r /etc/profile.d/modules.sh ]] || source /etc/profile.d/modules.sh
fi
module load intel/icc18 intel/mpi5
export CXX=icpc MPICXX=mpiicpc CXX_STANDARD=c++14
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
# Single-node measurements: shared-memory transport and one core per rank.
export I_MPI_FABRICS=shm I_MPI_PIN=1 I_MPI_PIN_DOMAIN=core I_MPI_PIN_RESPECT_CPUSET=1
export I_MPI_DEBUG=4
set -u
result="$PWD/lab3_mpi/results_korolev/${SLURM_JOB_ID}-${mode}"
mkdir -p "$result"
{
    date -u
    hostname
    (set +u; module list) 2>&1
    icpc --version
    mpiicpc -show
    mpirun --version
    python3 --version
    lscpu
    taskset -pc $$
    scontrol show job "$SLURM_JOB_ID"
} > "$result/cluster_environment.txt" 2>&1
bash lab3_mpi/build_linux.sh "$result/build" 2>&1 | tee "$result/build.log"
python3 lab3_mpi/run_portable.py --mode "$mode" --inputs inputs \
    --serial "$result/build/matrix_serial" --mpi "$result/build/matrix_mpi" \
    --launcher 'bash lab3_mpi/slurm_mpirun.sh' \
    --out "$result" --label "korolev-${SLURM_JOB_ID}" \
    2>&1 | tee "$result/run.log"
