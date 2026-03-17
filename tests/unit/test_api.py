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
from rsrf.manifests import manifest_path
from rsrf.ingest import write_band_spec_artifacts
from rsrf.models import BandSpec, SampledCurve
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
    ("sentinel-3b_olci", "band_average"),
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

    def test_load_curve_reads_landsat4_tm_with_correct_axis_orientation(self) -> None:
        curve = load_curve("landsat-4_tm", "B2", "band_average", root=ROOT)
        peak_index = max(range(len(curve.response)), key=lambda index: float(curve.response[index]))

        self.assertIsInstance(curve, SampledCurve)
        self.assertGreater(min(curve.wavelength_nm), 400.0)
        self.assertLess(max(curve.response), 1.01)
        self.assertAlmostEqual(curve.wavelength_nm[peak_index], 594.0, delta=5.0)

    def test_load_curve_reads_planet_support_article_variants(self) -> None:
        rapideye = load_curve("rapideye_msi", "RedEdge", "official_rsr", root=ROOT)
        superdove = load_curve("planetscope_psb_sd", "CoastalBlue", "superdove", root=ROOT)
        skysat = load_curve("skysat_msi", "Pan", "skysat14_19", root=ROOT)

        self.assertIsInstance(rapideye, SampledCurve)
        self.assertIsInstance(superdove, SampledCurve)
        self.assertIsInstance(skysat, SampledCurve)
        self.assertGreater(len(rapideye.wavelength_nm), 100)
        self.assertGreater(len(superdove.wavelength_nm), 100)
        self.assertGreater(len(skysat.wavelength_nm), 100)

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

    def test_load_band_spec_reads_enmap_and_emit_band_specs(self) -> None:
        enmap = load_band_spec("enmap_hsi", "B001", "metadata_band_spec", root=ROOT)
        emit = load_band_spec("emit_hsi", "B001", "metadata_band_spec", root=ROOT)

        self.assertIsInstance(enmap, BandSpec)
        self.assertIsInstance(emit, BandSpec)
        self.assertEqual(enmap.band_id, "B001")
        self.assertEqual(emit.band_id, "B001")
        self.assertGreater(enmap.center_wavelength_nm, 400.0)
        self.assertGreater(emit.center_wavelength_nm, 300.0)

    def test_load_band_spec_reads_prisma_band_spec(self) -> None:
        prisma = load_band_spec("prisma_hsi", "B001", "metadata_band_spec", root=ROOT)

        self.assertIsInstance(prisma, BandSpec)
        self.assertEqual(prisma.band_id, "B001")
        self.assertEqual(prisma.band_name, "VNIR001")
        self.assertAlmostEqual(prisma.center_wavelength_nm, 1003.6806030273438)
        self.assertEqual(prisma.shape_param_json["subsystem"], "VNIR")

    def test_load_band_spec_reads_satellogic_variants(self) -> None:
        mark_iv = load_band_spec("satellogic_newsat_msi", "Blue", "mark_iv_band_spec", root=ROOT)
        mark_v = load_band_spec("satellogic_newsat_msi", "Blue", "mark_v_band_spec", root=ROOT)
        hsi = load_band_spec("satellogic_newsat_hsi", "B01", "mark_iv_band_spec", root=ROOT)

        self.assertIsInstance(mark_iv, BandSpec)
        self.assertIsInstance(mark_v, BandSpec)
        self.assertIsInstance(hsi, BandSpec)
        self.assertAlmostEqual(mark_iv.center_wavelength_nm, 480.0)
        self.assertAlmostEqual(mark_v.center_wavelength_nm, 483.5)
        self.assertAlmostEqual(hsi.center_wavelength_nm, 483.0)

    def test_load_band_spec_reads_promoted_public_interval_variants(self) -> None:
        pleiades = load_band_spec("pleiades_msi", "Blue", "metadata_band_spec", root=ROOT)
        neo = load_band_spec("pleiades-neo_msi", "RedEdge", "metadata_band_spec", root=ROOT)
        spot = load_band_spec("spot-6_7_msi", "Pan", "metadata_band_spec", root=ROOT)
        formosat = load_band_spec("formosat-5_rsi", "NIR", "metadata_band_spec", root=ROOT)
        amazonia = load_band_spec("amazonia-1_optical_imager", "NIR", "metadata_band_spec", root=ROOT)
        cbers = load_band_spec("cbers-4a_optical_payload", "Yellow", "wpm_band_spec", root=ROOT)

        self.assertIsInstance(pleiades, BandSpec)
        self.assertIsInstance(neo, BandSpec)
        self.assertIsInstance(spot, BandSpec)
        self.assertIsInstance(formosat, BandSpec)
        self.assertIsInstance(amazonia, BandSpec)
        self.assertIsInstance(cbers, BandSpec)
        self.assertAlmostEqual(pleiades.center_wavelength_nm, 490.0)
        self.assertAlmostEqual(neo.center_wavelength_nm, 725.0)
        self.assertAlmostEqual(spot.center_wavelength_nm, 600.0)
        self.assertAlmostEqual(formosat.center_wavelength_nm, 830.0)
        self.assertAlmostEqual(amazonia.center_wavelength_nm, 830.0)
        self.assertAlmostEqual(cbers.center_wavelength_nm, 610.0)
        self.assertEqual(cbers.shape_param_json["center_source"], "midpoint_of_support_range")

    def test_load_curve_reads_probav_camera_variant(self) -> None:
        curve = load_curve("probav_vgt", "BLUE", "center_camera", root=ROOT)

        self.assertIsInstance(curve, SampledCurve)
        self.assertEqual(curve.band_id, "BLUE")
        self.assertGreater(len(curve.wavelength_nm), 10)

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
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json"))
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
