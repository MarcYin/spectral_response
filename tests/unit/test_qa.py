from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.ingest import write_band_spec_artifacts
from rsrf.io import read_json
from rsrf.parsers.band_spec_table import parse_band_spec_table
from rsrf.qa import validate_sensor, write_validation_artifacts
from rsrf.validate import parse_manifest_dict


class QaTests(unittest.TestCase):
    def test_validate_sampled_curve_variant_passes_for_sentinel2(self) -> None:
        report = validate_sensor("sentinel-2c_msi", "band_average", root=ROOT)

        self.assertEqual(report["content_kind"], "sampled_curve")
        self.assertTrue(report["passed"])
        self.assertEqual(report["failure_count"], 0)
        self.assertEqual(report["summary"]["band_count"], 13)
        self.assertIn("B03", report["band_metrics"])

    def test_validate_band_spec_variant_reports_realization_checks(self) -> None:
        report = validate_sensor("hyperspec_example", "metadata_band_spec", root=ROOT)

        self.assertEqual(report["content_kind"], "band_spec")
        self.assertTrue(report["passed"])
        self.assertEqual(report["failure_count"], 0)
        self.assertTrue(report["realization_checks"]["enabled"])
        self.assertLess(report["realization_checks"]["max_center_abs_error_nm"], 1.0)
        self.assertLess(report["realization_checks"]["max_fwhm_abs_error_nm"], 2.0)

    def test_write_validation_artifacts_exports_report_and_plot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "sentinel_validation"
            written = write_validation_artifacts(
                "sentinel-2c_msi",
                "band_average",
                root=ROOT,
                output_dir=output_dir,
            )

            self.assertTrue(written["report"].exists())
            self.assertTrue(written["plot"].exists())
            self.assertGreater(written["plot"].stat().st_size, 0)

            report = read_json(written["report"])
            self.assertEqual(report["sensor_unit_id"], "sentinel-2c_msi")
            self.assertTrue(report["passed"])

    def test_validate_band_spec_variant_reports_invalid_fwhm_without_crashing(self) -> None:
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
            report = validate_sensor("hyperspec_example", "metadata_band_spec", root=tmp_root)

        self.assertFalse(report["passed"])
        self.assertGreaterEqual(report["failure_count"], 1)
        checks = {failure["check"] for failure in report["failures"]}
        self.assertIn("positive_fwhm", checks)

    def test_validate_band_spec_variant_reports_unsupported_realization_recipe(self) -> None:
        payload = read_json(ROOT / "rsrf_source_manifest_hyperspectral_band_spec_example.json")
        payload["curve_realization"]["profile_type"] = "triangle"
        manifest = parse_manifest_dict(payload)
        artifacts = parse_band_spec_table(ROOT / manifest.raw_local_path, manifest)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            write_band_spec_artifacts(tmp_root, manifest, artifacts)
            report = validate_sensor("hyperspec_example", "metadata_band_spec", root=tmp_root)

        self.assertFalse(report["passed"])
        self.assertGreaterEqual(report["failure_count"], 1)
        checks = {failure["check"] for failure in report["failures"]}
        self.assertIn("realization_recipe", checks)


if __name__ == "__main__":
    unittest.main()
