from __future__ import annotations

import io
import json
import os
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
from rsrf.manifests import PLANNING_MANIFEST_DIRNAME, manifest_path
from rsrf.parsers.band_spec_table import parse_band_spec_table
from rsrf.validate import parse_manifest_dict

EXPECTED_CANONICAL_VARIANTS = {
    ("amazonia-1_optical_imager", "metadata_band_spec"),
    ("adeos_octs", "band_average"),
    ("aqua_modis", "band_average"),
    ("cbers-4a_optical_payload", "mux_band_spec"),
    ("cbers-4a_optical_payload", "wfi_band_spec"),
    ("cbers-4a_optical_payload", "wpm_band_spec"),
    ("emit_hsi", "metadata_band_spec"),
    ("enmap_hsi", "metadata_band_spec"),
    ("envisat_meris", "band_average"),
    ("formosat-5_rsi", "metadata_band_spec"),
    ("hyperspec_example", "metadata_band_spec"),
    ("landsat-1_mss", "band_average"),
    ("landsat-2_mss", "band_average"),
    ("landsat-3_mss", "band_average"),
    ("landsat-4_mss", "band_average"),
    ("landsat-4_tm", "band_average"),
    ("landsat-5_mss", "band_average"),
    ("landsat-5_tm", "band_average"),
    ("landsat-7_etm_plus", "band_average"),
    ("landsat-8_oli", "band_average"),
    ("landsat-8_tirs", "band_average"),
    ("landsat-9_oli2", "band_average"),
    ("landsat-9_tirs2", "band_average"),
    ("nimbus-7_czcs", "band_average"),
    ("noaa-20_viirs", "band_average"),
    ("noaa-21_viirs", "band_average"),
    ("orbview-2_seawifs", "band_average"),
    ("pace_oci", "l1b_band_spec"),
    ("pleiades-neo_msi", "metadata_band_spec"),
    ("pleiades_msi", "metadata_band_spec"),
    ("planetscope_ps2", "satid_0c_0d"),
    ("planetscope_ps2", "satid_0e"),
    ("planetscope_ps2", "satid_0f_10"),
    ("planetscope_ps2_sd", "dove_r"),
    ("planetscope_psb_sd", "superdove"),
    ("probav_vgt", "center_camera"),
    ("probav_vgt", "left_camera"),
    ("probav_vgt", "right_camera"),
    ("prisma_hsi", "metadata_band_spec"),
    ("rapideye_msi", "official_rsr"),
    ("satellogic_newsat_hsi", "mark_iv_band_spec"),
    ("satellogic_newsat_msi", "mark_iv_band_spec"),
    ("satellogic_newsat_msi", "mark_v_band_spec"),
    ("sentinel-2a_msi", "band_average"),
    ("sentinel-2b_msi", "band_average"),
    ("sentinel-2c_msi", "band_average"),
    ("sentinel-3a_olci", "band_average"),
    ("sentinel-3a_slstr", "band_average"),
    ("sentinel-3b_olci", "band_average"),
    ("sentinel-3b_slstr", "band_average"),
    ("spot-6_7_msi", "metadata_band_spec"),
    ("skysat_msi", "skysat1"),
    ("skysat_msi", "skysat2"),
    ("skysat_msi", "skysat3"),
    ("skysat_msi", "skysat4"),
    ("skysat_msi", "skysat5"),
    ("skysat_msi", "skysat6"),
    ("skysat_msi", "skysat7"),
    ("skysat_msi", "skysat8"),
    ("skysat_msi", "skysat9"),
    ("skysat_msi", "skysat10"),
    ("skysat_msi", "skysat11"),
    ("skysat_msi", "skysat12"),
    ("skysat_msi", "skysat13"),
    ("skysat_msi", "skysat14_19"),
    ("snpp_viirs", "band_average"),
    ("terra_aster", "band_average"),
    ("terra_modis", "band_average"),
}


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

    def test_validate_manifest_resolves_library_filename_with_root_outside_repo(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                exit_code, stdout = self._run_main(
                    [
                        "validate-manifest",
                        "rsrf_source_manifest_sentinel2c_v2.json",
                        "--root",
                        str(ROOT),
                    ]
                )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIn("Manifest OK: sentinel-2c_msi [band_average] sampled_curve", stdout)

    def test_version_flag_reports_package_version(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as context:
            main(["--version"])

        self.assertEqual(context.exception.code, 0)
        self.assertIn("rsrf 0.3.0", output.getvalue())

    def test_list_sensors_returns_available_sensor_representations(self) -> None:
        exit_code, stdout = self._run_main(["list-sensors", "--root", str(ROOT)])

        self.assertEqual(exit_code, 0)
        rows = json.loads(stdout)
        variants = {(row["sensor_unit_id"], row["representation_variant"]) for row in rows}
        self.assertEqual(variants, EXPECTED_CANONICAL_VARIANTS)

    def test_list_planned_sensors_returns_p2_catalog_entries(self) -> None:
        exit_code, stdout = self._run_main(["list-planned-sensors", "--root", str(ROOT)])

        self.assertEqual(exit_code, 0)
        rows = json.loads(stdout)
        self.assertEqual(rows, [])

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

    def test_show_response_summarizes_pace_oci_band_spec(self) -> None:
        exit_code, stdout = self._run_main(
            [
                "show-response",
                "pace_oci",
                "B001",
                "--variant",
                "l1b_band_spec",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["content_kind"], "band_spec")
        self.assertEqual(payload["band_id"], "B001")
        self.assertAlmostEqual(payload["center_wavelength_nm"], 314.55, places=2)

    def test_show_response_summarizes_satellogic_band_specs(self) -> None:
        msi_exit_code, msi_stdout = self._run_main(
            [
                "show-response",
                "satellogic_newsat_msi",
                "Blue",
                "--variant",
                "mark_iv_band_spec",
                "--root",
                str(ROOT),
            ]
        )
        hsi_exit_code, hsi_stdout = self._run_main(
            [
                "show-response",
                "satellogic_newsat_hsi",
                "B01",
                "--variant",
                "mark_iv_band_spec",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(msi_exit_code, 0)
        self.assertEqual(hsi_exit_code, 0)
        msi_payload = json.loads(msi_stdout)
        hsi_payload = json.loads(hsi_stdout)
        self.assertEqual(msi_payload["content_kind"], "band_spec")
        self.assertEqual(hsi_payload["content_kind"], "band_spec")

    def test_show_response_summarizes_enmap_and_emit_band_specs(self) -> None:
        enmap_exit_code, enmap_stdout = self._run_main(
            [
                "show-response",
                "enmap_hsi",
                "B001",
                "--variant",
                "metadata_band_spec",
                "--root",
                str(ROOT),
            ]
        )
        emit_exit_code, emit_stdout = self._run_main(
            [
                "show-response",
                "emit_hsi",
                "B001",
                "--variant",
                "metadata_band_spec",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(enmap_exit_code, 0)
        self.assertEqual(emit_exit_code, 0)
        enmap_payload = json.loads(enmap_stdout)
        emit_payload = json.loads(emit_stdout)
        self.assertEqual(enmap_payload["content_kind"], "band_spec")
        self.assertEqual(emit_payload["content_kind"], "band_spec")
        self.assertEqual(enmap_payload["band_id"], "B001")
        self.assertEqual(emit_payload["band_id"], "B001")

    def test_show_response_summarizes_prisma_band_spec(self) -> None:
        exit_code, stdout = self._run_main(
            [
                "show-response",
                "prisma_hsi",
                "B001",
                "--variant",
                "metadata_band_spec",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["content_kind"], "band_spec")
        self.assertEqual(payload["band_id"], "B001")
        self.assertEqual(payload["band_name"], "VNIR001")
        self.assertAlmostEqual(payload["center_wavelength_nm"], 1003.6806030273438)

    def test_show_response_summarizes_promoted_public_interval_band_specs(self) -> None:
        neo_exit_code, neo_stdout = self._run_main(
            [
                "show-response",
                "pleiades-neo_msi",
                "RedEdge",
                "--variant",
                "metadata_band_spec",
                "--root",
                str(ROOT),
            ]
        )
        cbers_exit_code, cbers_stdout = self._run_main(
            [
                "show-response",
                "cbers-4a_optical_payload",
                "Yellow",
                "--variant",
                "wpm_band_spec",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(neo_exit_code, 0)
        self.assertEqual(cbers_exit_code, 0)
        neo_payload = json.loads(neo_stdout)
        cbers_payload = json.loads(cbers_stdout)
        self.assertEqual(neo_payload["content_kind"], "band_spec")
        self.assertEqual(cbers_payload["content_kind"], "band_spec")
        self.assertAlmostEqual(neo_payload["center_wavelength_nm"], 725.0)
        self.assertAlmostEqual(cbers_payload["fwhm_nm"], 40.0)

    def test_show_response_summarizes_planet_support_article_curves(self) -> None:
        rapid_exit_code, rapid_stdout = self._run_main(
            [
                "show-response",
                "rapideye_msi",
                "RedEdge",
                "--variant",
                "official_rsr",
                "--root",
                str(ROOT),
            ]
        )
        superdove_exit_code, superdove_stdout = self._run_main(
            [
                "show-response",
                "planetscope_psb_sd",
                "CoastalBlue",
                "--variant",
                "superdove",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(rapid_exit_code, 0)
        self.assertEqual(superdove_exit_code, 0)
        rapid_payload = json.loads(rapid_stdout)
        superdove_payload = json.loads(superdove_stdout)
        self.assertEqual(rapid_payload["content_kind"], "sampled_curve")
        self.assertEqual(superdove_payload["content_kind"], "sampled_curve")

    def test_show_response_summarizes_probav_camera_variant(self) -> None:
        exit_code, stdout = self._run_main(
            [
                "show-response",
                "probav_vgt",
                "BLUE",
                "--variant",
                "center_camera",
                "--root",
                str(ROOT),
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["content_kind"], "sampled_curve")
        self.assertEqual(payload["band_id"], "BLUE")
        self.assertGreater(payload["sample_count"], 10)

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
        self.assertTrue(payload["overlay_checks"]["available"])

    def test_validate_sensor_returns_nonzero_when_report_has_failures(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json"))
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
                    "sentinel-2c_msi",
                    "--variant",
                    "band_average",
                    "--root",
                    str(ROOT),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("report:", stdout)
            self.assertIn("plot:", stdout)
            self.assertIn("overlay_plot:", stdout)
            self.assertTrue((output_dir / "validation_report.json").exists())
            self.assertTrue((output_dir / "overview.png").exists())
            self.assertTrue((output_dir / "overlay.png").exists())

    def test_register_planned_sensors_writes_registry_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            exit_code, stdout = self._run_main(
                [
                    "register-planned-sensors",
                    "--root",
                    str(tmpdir),
                    "--catalog-path",
                    str(
                        manifest_path(
                            ROOT,
                            "p2_planned_optical_sensors.json",
                            manifest_group=PLANNING_MANIFEST_DIRNAME,
                        )
                    ),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("No planned sensor rows were written.", stdout)


if __name__ == "__main__":
    unittest.main()
