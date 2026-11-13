"""The portable verifier must reject corrupted matrices and false timings."""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('portable', Path(__file__).with_name('run_portable.py'))
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)


class VerificationTests(unittest.TestCase):
    def test_digest_normalizes_windows_newlines(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'C.txt'
            path.write_bytes(b'2\n1 -2\n3 4\n')
            expected = portable.matrix_digest(path)
            path.write_bytes(b'2\r\n1 -2\r\n3 4\r\n')
            self.assertEqual(portable.matrix_digest(path), expected)
            portable.verify_matrix(path, expected)
            path.write_bytes(b'2\n1 -2\n3 5\n')
            with self.assertRaises(ValueError):
                portable.verify_matrix(path, expected)

    def test_statistics_match_requested_run(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'stats.csv'
            base = dict(n=3, processes=2, total_ms=2, compute_ms=1, gops=.001)
            for edits, valid in [({}, True), ({'n': 4}, False),
                                 ({'processes': 1}, False), ({'total_ms': 'nan'}, False),
                                 ({'compute_ms': -1}, False), ({'gops': 'inf'}, False)]:
                row = dict(base, **edits)
                with path.open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(row))
                    writer.writeheader(); writer.writerow(row)
                if valid:
                    self.assertEqual(portable.read_stats(path, 3, 2)['processes'], '2')
                else:
                    with self.assertRaises(ValueError):
                        portable.read_stats(path, 3, 2)


if __name__ == '__main__':
    unittest.main()
