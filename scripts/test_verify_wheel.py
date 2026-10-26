"""Regression: the verifier must boot its external venv with this Python build.

Run after building the wheel: python scripts/test_verify_wheel.py /path/to/wheel
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest


WHEEL = Path(sys.argv.pop(1)).resolve()


class VerifierTests(unittest.TestCase):
    def test_external_environment_boots_and_verifies_installed_wheel(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name('verify_wheel.py')), str(WHEEL)],
            capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout[result.stdout.rfind('\n{') + 1:])
        self.assertTrue(summary['outsideCheckout'])
        self.assertEqual(summary['sourcePathInjection'], 'REMOVED')


if __name__ == '__main__':
    unittest.main()
