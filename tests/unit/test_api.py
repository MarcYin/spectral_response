from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.api import (
    get_metadata,
    list_bands,
    list_sensors,
    load_band_spec,
    load_curve,
    load_response_definition,
)
from rsrf.io import read_json
from rsrf.ingest import write_band_spec_artifacts
from rsrf.models import BandSpec, SampledCurve
from rsrf.parsers.band_spec_table import parse_band_spec_table
from rsrf.validate import parse_manifest_dict

EXPECTED_CANONICAL_VARIANTS = {
    ("adeos_octs", "band_average"),
    ("aqua_modis", "band_average"),
    ("envisat_meris", "band_average"),
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
    ("sentinel-2a_msi", "band_average"),
    ("sentinel-2b_msi", "band_average"),
    ("sentinel-2c_msi", "band_average"),
    ("sentinel-3a_olci", "band_average"),
    ("sentinel-3b_olci", "band_average"),
    ("snpp_viirs", "band_average"),
    ("terra_aster", "band_average"),
    ("terra_modis", "band_average"),
}


class ApiTests(unittest.TestCase):
    def test_list_sensors_returns_registered_canonical_forms(self) -> None:
        sensors = list_sensors(ROOT)
        variants = {
            (row["sensor_unit_id"], row["representation_variant"])
            for row in sensors
        }
        self.assertEqual(variants, EXPECTED_CANONICAL_VARIANTS)

    def test_load_curve_reads_canonical_sampled_data(self) -> None:
        curve = load_curve("sentinel-2c_msi", "B01", "band_average", root=ROOT)
        self.assertIsInstance(curve, SampledCurve)
        self.assertEqual(curve.band_id, "B01")
        self.assertEqual(len(curve.wavelength_nm), 2301)

    def test_load_curve_reads_new_sentinel_platforms(self) -> None:
        curve_a = load_curve("sentinel-2a_msi", "B01", "band_average", root=ROOT)
        curve_b = load_curve("sentinel-2b_msi", "B01", "band_average", root=ROOT)

        self.assertIsInstance(curve_a, SampledCurve)
        self.assertIsInstance(curve_b, SampledCurve)
        self.assertEqual(len(curve_a.wavelength_nm), 2301)
        self.assertEqual(len(curve_b.wavelength_nm), 2301)

    def test_load_curve_reads_new_sensor_families(self) -> None:
        landsat_tirs = load_curve("landsat-8_tirs", "B10", "band_average", root=ROOT)
        viirs = load_curve("noaa-20_viirs", "M1", "band_average", root=ROOT)
        olci = load_curve("sentinel-3a_olci", "B01", "band_average", root=ROOT)
        seawifs = load_curve("orbview-2_seawifs", "B01", "band_average", root=ROOT)

        self.assertIsInstance(landsat_tirs, SampledCurve)
        self.assertIsInstance(viirs, SampledCurve)
        self.assertIsInstance(olci, SampledCurve)
        self.assertIsInstance(seawifs, SampledCurve)
        self.assertGreater(len(landsat_tirs.wavelength_nm), 10)
        self.assertGreater(len(viirs.wavelength_nm), 10)
        self.assertEqual(len(olci.wavelength_nm), 200)
        self.assertGreater(len(seawifs.wavelength_nm), 10)

    def test_load_band_spec_reads_canonical_band_spec(self) -> None:
        band_spec = load_band_spec(
            "hyperspec_example",
            "B001",
            "metadata_band_spec",
            root=ROOT,
        )
        self.assertIsInstance(band_spec, BandSpec)
        self.assertEqual(band_spec.band_id, "B001")
        self.assertAlmostEqual(band_spec.center_wavelength_nm, 410.0)

    def test_load_band_spec_reads_pace_oci_bandpass(self) -> None:
        band_spec = load_band_spec("pace_oci", "B001", "l1b_band_spec", root=ROOT)

        self.assertIsInstance(band_spec, BandSpec)
        self.assertEqual(band_spec.band_id, "B001")
        self.assertAlmostEqual(band_spec.center_wavelength_nm, 314.55, places=2)

    def test_load_response_definition_dispatches_by_content_kind(self) -> None:
        sampled = load_response_definition("sentinel-2c_msi", "B02", "band_average", root=ROOT)
        band_spec = load_response_definition(
            "hyperspec_example",
            "B002",
            "metadata_band_spec",
            root=ROOT,
        )
        self.assertIsInstance(sampled, SampledCurve)
        self.assertIsInstance(band_spec, BandSpec)

    def test_unbacked_realized_variant_is_not_exposed_by_read_api(self) -> None:
        with self.assertRaises(KeyError):
            load_response_definition(
                "hyperspec_example",
                "B001",
                "gaussian_from_fwhm",
                root=ROOT,
            )

    def test_list_bands_and_metadata_use_registry_outputs(self) -> None:
        sentinel_bands = list_bands("sentinel-2c_msi", "band_average", root=ROOT)
        hyperspec_metadata = get_metadata(
            "hyperspec_example",
            "metadata_band_spec",
            root=ROOT,
        )
        self.assertEqual(len(sentinel_bands), 13)
        self.assertEqual(hyperspec_metadata["band_spec_table"]["row_count"], 6)

    def test_persisted_realized_variant_is_exposed_by_read_api(self) -> None:
        payload = read_json(ROOT / "rsrf_source_manifest_hyperspectral_band_spec_example.json")
        payload["curve_realization"]["persist_realized_curves"] = True
        manifest = parse_manifest_dict(payload)
        artifacts = parse_band_spec_table(ROOT / manifest.raw_local_path, manifest)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            write_band_spec_artifacts(tmp_root, manifest, artifacts)

            sensors = list_sensors(tmp_root)
            variants = {
                (row["sensor_unit_id"], row["representation_variant"])
                for row in sensors
            }
            self.assertIn(("hyperspec_example", "gaussian_from_fwhm"), variants)

            realized_bands = list_bands(
                "hyperspec_example",
                "gaussian_from_fwhm",
                root=tmp_root,
            )
            realized_metadata = get_metadata(
                "hyperspec_example",
                "gaussian_from_fwhm",
                root=tmp_root,
            )
            realized_curve = load_curve(
                "hyperspec_example",
                "B001",
                "gaussian_from_fwhm",
                root=tmp_root,
            )

        self.assertEqual(len(realized_bands), 6)
        self.assertEqual(realized_metadata["content_kind"], "sampled_curve")
        self.assertEqual(
            realized_metadata["source_representation_variant"],
            "metadata_band_spec",
        )
        self.assertIsInstance(realized_curve, SampledCurve)
        self.assertEqual(realized_curve.source_variant, "gaussian_from_fwhm")
        self.assertGreater(len(realized_curve.wavelength_nm), 3)


if __name__ == "__main__":
    unittest.main()
