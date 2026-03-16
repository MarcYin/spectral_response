from __future__ import annotations

import io
import json
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
    def _run_main(self, argv: list[str]) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(argv)
        return exit_code, output.getvalue()

    def test_validate_manifest_reports_invalid_json_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "broken.json"
            manifest_path.write_text("{invalid json", encoding="utf-8")
            exit_code, stdout = self._run_main(["validate-manifest", str(manifest_path)])

        self.assertEqual(exit_code, 1)
        self.assertIn("Manifest validation failed", stdout)
        self.assertIn("manifest file is not valid JSON", stdout)

    def test_list_sensors_returns_available_sensor_representations(self) -> None:
        exit_code, stdout = self._run_main(["list-sensors", "--root", str(ROOT)])

        self.assertEqual(exit_code, 0)
        rows = json.loads(stdout)
        variants = {
            (row["sensor_unit_id"], row["representation_variant"])
            for row in rows
        }
        self.assertEqual(
            variants,
            {
                ("sentinel-2c_msi", "band_average"),
                ("hyperspec_example", "metadata_band_spec"),
            },
        )

    def test_list_bands_returns_canonical_band_rows(self) -> None:
        exit_code, stdout = self._run_main(
            [
                "list-bands",
                "sentinel-2c_msi",
                "--variant",
                "band_average",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(exit_code, 0)
        rows = json.loads(stdout)
        self.assertEqual(len(rows), 13)
        self.assertEqual(rows[0]["band_id"], "B01")
        self.assertEqual(rows[0]["band_index"], 1)
        self.assertEqual(rows[0]["native_sampling_nm"], 1.0)

    def test_show_metadata_returns_metadata_json(self) -> None:
        exit_code, stdout = self._run_main(
            [
                "show-metadata",
                "hyperspec_example",
                "--variant",
                "metadata_band_spec",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["sensor_unit_id"], "hyperspec_example")
        self.assertEqual(payload["band_spec_table"]["row_count"], 6)

    def test_show_metadata_reports_missing_sensor_cleanly(self) -> None:
        exit_code, stdout = self._run_main(
            [
                "show-metadata",
                "missing_sensor",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("sensor representation not found", stdout)

    def test_show_response_summarizes_sampled_curve(self) -> None:
        exit_code, stdout = self._run_main(
            [
                "show-response",
                "sentinel-2c_msi",
                "B02",
                "--variant",
                "band_average",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["content_kind"], "sampled_curve")
        self.assertEqual(payload["band_id"], "B02")
        self.assertEqual(payload["sample_count"], 2301)
        self.assertGreater(payload["area"], 0.0)

    def test_show_response_summarizes_band_spec(self) -> None:
        exit_code, stdout = self._run_main(
            [
                "show-response",
                "hyperspec_example",
                "B004",
                "--variant",
                "metadata_band_spec",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["content_kind"], "band_spec")
        self.assertEqual(payload["band_id"], "B004")
        self.assertAlmostEqual(payload["center_wavelength_nm"], 441.5)
        self.assertAlmostEqual(payload["fwhm_nm"], 9.5)


if __name__ == "__main__":
    unittest.main()
