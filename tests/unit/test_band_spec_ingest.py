from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.ingest import write_band_spec_artifacts
from rsrf.io import read_json
from rsrf.manifests import manifest_path
from rsrf.parsers.band_spec_table import parse_band_spec_table
from rsrf.registry import read_registry_table
from rsrf.validate import parse_manifest_dict


class BandSpecIngestTests(unittest.TestCase):
    def test_write_band_spec_artifacts_updates_registry(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json"))
        manifest = parse_manifest_dict(payload)
        artifacts = parse_band_spec_table(ROOT / manifest.raw_local_path, manifest)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            written = write_band_spec_artifacts(tmp_root, manifest, artifacts)
            self.assertIn("band_specs", written)
            band_specs = read_registry_table(tmp_root, "band_specs")
            realizations = read_registry_table(tmp_root, "realizations")
            self.assertEqual(len(band_specs), 6)
            self.assertEqual(len(realizations), 1)
            metadata = json.loads(
                (
                    tmp_root
                    / "data"
                    / "canonical"
                    / "band_spec"
                    / manifest.sensor_unit_id
                    / manifest.representation_variant
                    / "metadata.json"
                ).read_text()
            )
            self.assertEqual(metadata["band_spec_table"]["row_count"], 6)

    def test_write_band_spec_artifacts_can_persist_realized_curves(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json"))
        payload["curve_realization"]["persist_realized_curves"] = True
        manifest = parse_manifest_dict(payload)
        artifacts = parse_band_spec_table(ROOT / manifest.raw_local_path, manifest)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            written = write_band_spec_artifacts(tmp_root, manifest, artifacts)

            self.assertIn("realized_curves", written)
            self.assertIn("realized_metadata", written)

            realized_curves = read_registry_table(tmp_root, "bands")
            realized_curves = realized_curves[realized_curves["representation_variant"] == "gaussian_from_fwhm"]
            self.assertEqual(len(realized_curves), 6)
            self.assertTrue(realized_curves["has_sampled_curve"].all())

            realized_metadata = read_json(
                tmp_root / "data" / "realized" / manifest.sensor_unit_id / "gaussian_from_fwhm" / "metadata.json"
            )
            self.assertEqual(realized_metadata["content_kind"], "sampled_curve")
            self.assertEqual(
                realized_metadata["derived_from"]["representation_variant"],
                manifest.representation_variant,
            )
            self.assertLess(realized_metadata["validation"]["max_center_abs_error_nm"], 1.0)
            self.assertLess(realized_metadata["validation"]["max_fwhm_abs_error_nm"], 2.0)

    def test_write_band_spec_artifacts_preflights_realized_curve_recipe(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json"))
        payload["curve_realization"]["persist_realized_curves"] = True
        payload["curve_realization"]["profile_type"] = "triangle"
        manifest = parse_manifest_dict(payload)
        artifacts = parse_band_spec_table(ROOT / manifest.raw_local_path, manifest)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            with self.assertRaisesRegex(NotImplementedError, "unsupported realized profile_type"):
                write_band_spec_artifacts(tmp_root, manifest, artifacts)

            self.assertFalse(
                (
                    tmp_root
                    / "data"
                    / "canonical"
                    / "band_spec"
                    / manifest.sensor_unit_id
                    / manifest.representation_variant
                    / "band_specs.parquet"
                ).exists()
            )
            self.assertFalse((tmp_root / "data" / "registry" / "sensors.parquet").exists())


if __name__ == "__main__":
    unittest.main()
