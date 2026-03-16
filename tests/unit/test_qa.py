from __future__ import annotations

import shutil
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
        self.assertTrue(report["overlay_checks"]["available"])
        self.assertEqual(report["overlay_checks"]["band_count"], 13)

    def test_validate_additional_sentinel_platform_passes(self) -> None:
        report = validate_sensor("sentinel-2a_msi", "band_average", root=ROOT)

        self.assertTrue(report["passed"])
        self.assertTrue(report["overlay_checks"]["available"])
        self.assertEqual(report["summary"]["band_count"], 13)

    def test_validate_sampled_curve_variant_fails_when_required_overlay_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            shutil.copytree(ROOT / "data", tmp_root / "data")

            report = validate_sensor("sentinel-2c_msi", "band_average", root=tmp_root)

        self.assertFalse(report["passed"])
        self.assertEqual(report["overlay_checks"]["available"], False)
        self.assertTrue(
            any(failure["check"] == "overlay_reference_missing" for failure in report["failures"])
        )

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
            self.assertTrue(written["overlay_plot"].exists())
            self.assertGreater(written["plot"].stat().st_size, 0)
            self.assertGreater(written["overlay_plot"].stat().st_size, 0)

            report = read_json(written["report"])
            self.assertEqual(report["sensor_unit_id"], "sentinel-2c_msi")
            self.assertTrue(report["passed"])

    def test_write_validation_artifacts_tolerates_invalid_overlay_reference_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            shutil.copytree(
                ROOT / "data",
                tmp_root / "data",
                copy_function=shutil.copyfile,
            )
            shutil.copytree(
                ROOT / "sources",
                tmp_root / "sources",
                copy_function=shutil.copyfile,
            )
            overlay_path = (
                tmp_root
                / "sources"
                / "extracted"
                / "sentinel-2c_msi"
                / "band_average"
                / "overlay_reference.csv"
            )
            overlay_lines = overlay_path.read_text(encoding="utf-8").splitlines()
            overlay_path.write_text(
                "\n".join([overlay_lines[0], overlay_lines[1], "B99,300,0.0"]) + "\n",
                encoding="utf-8",
            )

            written = write_validation_artifacts(
                "sentinel-2c_msi",
                "band_average",
                root=tmp_root,
                output_dir=tmp_root / "validation",
            )
            self.assertTrue(written["report"].exists())
            self.assertTrue(written["plot"].exists())
            self.assertTrue(written["overlay_plot"].exists())
            report = read_json(written["report"])
            self.assertFalse(report["passed"])
            self.assertTrue(
                any(
                    failure["check"] == "overlay_reference_band_missing"
                    for failure in report["failures"]
                )
            )

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
