from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.manifests import iter_source_manifest_paths, manifest_path
from rsrf.models import ContentKind, ManifestValidationError
from rsrf.validate import parse_manifest_dict, parse_manifest_file, validate_manifest_dict


class ManifestValidationTests(unittest.TestCase):
    def test_sampled_curve_manifest_is_valid(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_sentinel2c_v2.json"))
        self.assertEqual(validate_manifest_dict(payload), [])

    def test_all_versioned_manifests_are_valid(self) -> None:
        for manifest_file in iter_source_manifest_paths(ROOT):
            if manifest_file.name == "rsrf_source_manifest_template_v2.json":
                continue
            payload = read_json(manifest_file)
            self.assertEqual(validate_manifest_dict(payload), [])

    def test_band_spec_manifest_is_valid(self) -> None:
        payload = read_json(
            manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json")
        )
        self.assertEqual(validate_manifest_dict(payload), [])

    def test_manifest_round_trip_preserves_core_fields(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_sentinel2c_v2.json"))
        manifest = parse_manifest_dict(payload)
        self.assertEqual(manifest.content_kind, ContentKind.SAMPLED_CURVE)
        self.assertEqual(manifest.parser.script, "scripts/ingest/ingest_sentinel2_srf.py")
        self.assertEqual(manifest.to_dict()["sensor_unit_id"], "sentinel-2c_msi")
        self.assertEqual(manifest.to_dict()["mission_family"], "Sentinel-2")

    def test_manifest_rejects_nonpositive_grid_policy_values(self) -> None:
        payload = read_json(
            manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json")
        )
        payload["curve_realization"]["grid_policy"]["samples_per_fwhm"] = 0
        errors = validate_manifest_dict(payload)
        self.assertIn(
            "curve_realization.grid_policy.samples_per_fwhm must be positive",
            errors,
        )

    def test_approximation_requires_reason(self) -> None:
        payload = read_json(
            manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json")
        )
        payload["curve_realization"]["approximation_reason"] = None
        errors = validate_manifest_dict(payload)
        self.assertIn(
            "curve_realization.approximation_reason is required when approximation=true",
            errors,
        )

    def test_manifest_requires_reason_for_top_level_approximation(self) -> None:
        payload = read_json(
            manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json")
        )
        payload["approximation"] = True
        payload["approximation_reason"] = None
        errors = validate_manifest_dict(payload)
        self.assertIn("approximation_reason is required when approximation=true", errors)

    def test_parse_manifest_file_reports_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "broken.json"
            manifest_path.write_text("{invalid json", encoding="utf-8")
            with self.assertRaises(ManifestValidationError) as context:
                parse_manifest_file(manifest_path)
        self.assertIn("manifest file is not valid JSON", context.exception.errors[0])


if __name__ == "__main__":
    unittest.main()
