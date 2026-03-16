from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.cli import main


class CliTests(unittest.TestCase):
    def test_validate_manifest_reports_invalid_json_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "broken.json"
            manifest_path.write_text("{invalid json", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["validate-manifest", str(manifest_path)])

        self.assertEqual(exit_code, 1)
        self.assertIn("Manifest validation failed", output.getvalue())
        self.assertIn("manifest file is not valid JSON", output.getvalue())


if __name__ == "__main__":
    unittest.main()
