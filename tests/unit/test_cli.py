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
from rsrf.ingest import write_band_spec_artifacts
from rsrf.io import read_json
from rsrf.parsers.band_spec_table import parse_band_spec_table
from rsrf.validate import parse_manifest_dict


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

    def test_validate_sensor_prints_qa_report_json(self) -> None:
        exit_code, stdout = self._run_main(
            [
                "validate-sensor",
                "sentinel-2c_msi",
                "--variant",
                "band_average",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["content_kind"], "sampled_curve")
        self.assertEqual(payload["summary"]["band_count"], 13)

    def test_validate_sensor_returns_nonzero_when_report_has_failures(self) -> None:
        payload = read_json(ROOT / "rsrf_source_manifest_hyperspectral_band_spec_example.json")
        manifest = parse_manifest_dict(payload)
        artifacts = parse_band_spec_table(ROOT / manifest.raw_local_path, manifest)
        artifacts.band_spec_rows[0] = dict(artifacts.band_spec_rows[0])
        artifacts.band_rows[0] = dict(artifacts.band_rows[0])
        artifacts.band_spec_rows[0]["fwhm_nm"] = 0.0
        artifacts.band_rows[0]["fwhm_nm"] = 0.0

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            write_band_spec_artifacts(tmp_root, manifest, artifacts)
            exit_code, stdout = self._run_main(
                [
                    "validate-sensor",
                    "hyperspec_example",
                    "--variant",
                    "metadata_band_spec",
                    "--root",
                    str(tmp_root),
                ]
            )

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout)
        self.assertFalse(payload["passed"])
        checks = {failure["check"] for failure in payload["failures"]}
        self.assertIn("positive_fwhm", checks)

    def test_export_validation_writes_report_and_plot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "validation"
            exit_code, stdout = self._run_main(
                [
                    "export-validation",
                    "hyperspec_example",
                    "--variant",
                    "metadata_band_spec",
                    "--root",
                    str(ROOT),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("report:", stdout)
            self.assertIn("plot:", stdout)
            self.assertTrue((output_dir / "validation_report.json").exists())
            self.assertTrue((output_dir / "overview.png").exists())


if __name__ == "__main__":
    unittest.main()
