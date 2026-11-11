"""Exercise shell orchestration with fake tools; this does not emulate a cluster."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash') if os.name != 'nt' else r'C:\Program Files\Git\bin\bash.exe'


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'experiments/work').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'experiments/work')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ('lab3_mpi', 'common', 'bin'):
            (self.root/folder).mkdir()
        for name in ('submit_slurm.sh', 'job.slurm', 'build_linux.sh'):
            shutil.copyfile(ROOT/'lab3_mpi'/name, self.root/'lab3_mpi'/name)
        for name in ('common/matrix.hpp', 'lab3_mpi/main.cpp', 'lab3_mpi/serial.cpp'):
            (self.root/name).write_text('test fixture\n')
        self.script('icpc', 'if [[ "$1" == --version ]]; then echo fake-compiler; exit; fi\n'
                    '[[ "${FAIL_BUILD:-0}" != 1 ]] || exit 42\n'
                    'printf "test executable\\n" > "${!#}"\nchmod +x "${!#}"\n')
        self.script('mpiicpc', 'if [[ "$1" == -show || "$1" == --version ]]; then echo fake-mpi-compiler; exit; fi\n'
                    'printf "test executable\\n" > "${!#}"\nchmod +x "${!#}"\n')
        self.script('sbatch', 'printf "%s\\n" "$@" > submission.txt\necho SIMULATED_SUBMISSION\n')
        for name in ('g++', 'mpirun', 'python3', 'lscpu', 'taskset', 'scontrol'):
            self.script(name, 'echo fake-tool\n')

    def script(self, name, body):
        path = self.root/'bin'/name
        path.write_text('#!/bin/bash\nset -e\n' + body, newline='\n')
        path.chmod(0o755)

    def run_shell(self, command):
        init = 'export PATH="$PWD/bin:$PATH"; module() { :; }; export -f module; '
        return subprocess.run([BASH, '-c', init+command], cwd=self.root,
                              capture_output=True, text=True, encoding='utf-8')

    def test_failed_build_is_never_submitted(self):
        run = self.run_shell('export FAIL_BUILD=1; bash lab3_mpi/submit_slurm.sh smoke')
        self.assertEqual(run.returncode, 42, run.stdout+run.stderr)
        self.assertFalse((self.root/'submission.txt').exists())

    def test_submission_and_compute_job_use_prebuilt_files(self):
        run = self.run_shell('bash lab3_mpi/submit_slurm.sh smoke')
        self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
        submitted = (self.root/'submission.txt').read_text()
        self.assertIn('--time=00:10:00', submitted)
        self.assertIn('LAB3_BUILD_DIR=', submitted)
        # Any compiler call on the compute node fails this regression test.
        self.script('icpc', 'exit 77\n')
        self.script('mpiicpc', 'exit 77\n')
        run = self.run_shell('export SLURM_JOB_ID=123 SLURM_JOB_NUM_NODES=1 SLURM_NTASKS=8; '
                             'export SLURM_SUBMIT_DIR="$PWD"; '
                             'export LAB3_BUILD_DIR="$(find "$PWD/build" -maxdepth 1 -type d -name "korolev.*")"; '
                             'bash lab3_mpi/job.slurm smoke')
        self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
        result = self.root/'lab3_mpi/results_korolev/123-smoke'
        self.assertTrue((result/'build/matrix_mpi').is_file())
        self.assertTrue((result/'build.log').is_file())
        self.assertTrue((result/'build_environment.txt').is_file())

    def test_submission_wrapper_refuses_compute_node(self):
        run = self.run_shell('export SLURM_JOB_ID=123; bash lab3_mpi/submit_slurm.sh smoke')
        self.assertNotEqual(run.returncode, 0)
        self.assertFalse((self.root/'submission.txt').exists())

    def test_corrupted_binary_is_rejected_before_run(self):
        run = self.run_shell('bash lab3_mpi/submit_slurm.sh smoke')
        self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
        folder = next((self.root/'build').glob('korolev.*'))
        (folder/'matrix_mpi').write_text('modified executable\n')
        self.script('python3', 'touch runner-was-called\n')
        run = self.run_shell('export SLURM_JOB_ID=124 SLURM_JOB_NUM_NODES=1 SLURM_NTASKS=8; '
                             'export SLURM_SUBMIT_DIR="$PWD"; '
                             'export LAB3_BUILD_DIR="$(find "$PWD/build" -maxdepth 1 -type d -name "korolev.*")"; '
                             'bash lab3_mpi/job.slurm smoke')
        self.assertNotEqual(run.returncode, 0, run.stdout+run.stderr)
        self.assertIn('matrix_mpi: FAILED', run.stdout)
        self.assertFalse((self.root/'runner-was-called').exists())


if __name__ == '__main__':
    unittest.main()
