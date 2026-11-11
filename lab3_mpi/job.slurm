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

# From the login node: bash lab3_mpi/submit_slurm.sh smoke (then full after success).
set -eo pipefail
: "${SLURM_JOB_ID:?Use sbatch, not bash, to start this script}"
: "${SLURM_SUBMIT_DIR:?Missing submission directory}"
: "${LAB3_BUILD_DIR:?Submit using bash lab3_mpi/submit_slurm.sh smoke or full}"
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
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
# Single-node measurements: shared-memory transport and one core per rank.
export I_MPI_FABRICS=shm I_MPI_PIN=1 I_MPI_PIN_DOMAIN=core I_MPI_PIN_RESPECT_CPUSET=1
export I_MPI_DEBUG=4
set -u
result="$PWD/lab3_mpi/results_korolev/${SLURM_JOB_ID}-${mode}"
mkdir -p "$result/build"
# All compilation happens before submission. Copy the specific build for this job.
for name in matrix_serial matrix_mpi binaries.sha256 sources.sha256 build.log build_environment.txt; do
    [[ -f "$LAB3_BUILD_DIR/$name" ]] || { echo "Missing prebuilt file: $name" >&2; exit 1; }
    cp -p "$LAB3_BUILD_DIR/$name" "$result/build/$name"
done
(cd "$result/build" && sha256sum -c binaries.sha256)
sha256sum -c "$result/build/sources.sha256"
cp -p "$result/build/build.log" "$result/build.log"
cp -p "$result/build/build_environment.txt" "$result/build_environment.txt"
{
    date -u
    hostname
    (set +u; module list) 2>&1
    mpirun --version
    python3 --version
    lscpu
    taskset -pc $$
    scontrol show job "$SLURM_JOB_ID"
} > "$result/cluster_environment.txt" 2>&1
# Diagnostic only; the smoke run checks whether the binaries actually load.
{ ldd "$result/build/matrix_serial"; ldd "$result/build/matrix_mpi"; } \
    > "$result/runtime_libraries.txt" 2>&1 || true
python3 lab3_mpi/run_portable.py --mode "$mode" --inputs inputs \
    --serial "$result/build/matrix_serial" --mpi "$result/build/matrix_mpi" \
    --launcher 'bash lab3_mpi/slurm_mpirun.sh' \
    --out "$result" --label "korolev-${SLURM_JOB_ID}" \
    2>&1 | tee "$result/run.log"
