"""Check baseline arithmetic and reject invalid comparisons, without a cluster."""
import csv
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SerialSummaryTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'experiments/work').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'experiments/work')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.mpi = self.folder/'mpi'
        self.serial = self.folder/'serial'
        self.mpi.mkdir(); self.serial.mkdir()
        self.rows = [dict(n=3,processes=p,total_ms=t,compute_ms=t,gops=1,
                          verified=True,label='same-machine') for p,t in [(1,10),(2,6)]]
        self.write(self.mpi, self.rows)

    def write(self, folder, rows):
        with (folder/'raw.csv').open('w',newline='') as f:
            writer = csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)

    def run_summary(self):
        env = dict(os.environ, MPLCONFIGDIR=str(self.folder/'mpl'))
        return subprocess.run([sys.executable,str(ROOT/'experiments/summarize.py'),'mpi',
                               '--input',str(self.mpi),'--serial-input',str(self.serial)],
                              env=env,text=True,capture_output=True)

    def test_speedup_uses_separate_serial_baseline(self):
        self.write(self.serial,[dict(self.rows[0],total_ms=8)])
        result = self.run_summary()
        self.assertEqual(result.returncode,0,result.stderr)
        with (self.mpi/'summary.csv').open() as f:
            parallel = next(r for r in csv.DictReader(f) if r['config']=='2')
        self.assertAlmostEqual(float(parallel['speedup_serial']),8/6)
        self.assertAlmostEqual(float(parallel['efficiency_serial']),8/6/2)
        self.assertAlmostEqual(float(parallel['speedup']),10/6)

    def test_unverified_baseline_is_rejected(self):
        self.write(self.serial,[dict(self.rows[0],verified=False)])
        result = self.run_summary()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Unverified serial row',result.stderr)

    def test_different_run_labels_are_rejected(self):
        self.write(self.serial,[dict(self.rows[0],label='another-machine')])
        result = self.run_summary()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Serial/MPI labels differ',result.stderr)

    def test_missing_size_is_rejected(self):
        self.write(self.serial,[dict(self.rows[0],n=7)])
        result = self.run_summary()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Missing serial baseline',result.stderr)

if __name__=='__main__': unittest.main()
