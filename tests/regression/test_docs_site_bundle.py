from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.docs_site import (
    VISUALIZATION_BUILD_ID,
    prepare_docs_site,
    visualization_css_bundle_filename,
    visualization_js_bundle_filename,
)


class DocsSiteBundleRegressionTests(unittest.TestCase):
    def test_mkdocs_build_uses_active_visualization_bundle(self) -> None:
        prepare_docs_site(ROOT, refresh_visualization_data=True)
        subprocess.run(
            [sys.executable, "-m", "mkdocs", "build", "--strict"],
            cwd=ROOT,
            check=True,
        )

        html = (ROOT / "site" / "visualizations" / "index.html").read_text(encoding="utf-8")
        self.assertIn(visualization_css_bundle_filename(), html)
        self.assertIn(visualization_js_bundle_filename(), html)
        self.assertIn(f'data-viz-version="{VISUALIZATION_BUILD_ID}"', html)
        self.assertIn('id="rsrf-toggle-pan-bands"', html)


if __name__ == "__main__":
    unittest.main()
