from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.parsers.multiband_curve_csv import parse_multiband_curve_csv
from rsrf.validate import parse_manifest_file


class MultiBandCurveCsvParserTests(unittest.TestCase):
    def test_parser_reads_superdove_support_attachment(self) -> None:
        manifest = parse_manifest_file(
            ROOT / "rsrf_source_manifest_planetscope_psb_sd_superdove_v2.json"
        )
        artifacts = parse_multiband_curve_csv(ROOT / manifest.raw_local_path, manifest)

        self.assertEqual(len(artifacts.band_rows), 8)
        band_ids = [row["band_id"] for row in artifacts.band_rows]
        self.assertEqual(
            band_ids,
            ["CoastalBlue", "Blue", "GreenI", "GreenII", "Yellow", "Red", "RedEdge", "NIR"],
        )
        self.assertEqual(artifacts.metadata["curve_csv"]["wavelength_field"], "Wavelength (nm)")

    def test_parser_reads_ps2_attachment_with_wl_header(self) -> None:
        manifest = parse_manifest_file(
            ROOT / "rsrf_source_manifest_planetscope_ps2_satid_0e_v2.json"
        )
        artifacts = parse_multiband_curve_csv(ROOT / manifest.raw_local_path, manifest)

        self.assertEqual(len(artifacts.band_rows), 4)
        self.assertEqual([row["band_id"] for row in artifacts.band_rows], ["Blue", "Green", "Red", "NIR"])
        self.assertGreater(len(artifacts.curve_rows), 100)


if __name__ == "__main__":
    unittest.main()
