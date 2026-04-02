from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.manifests import manifest_path
from rsrf.parsers.obpg import parse_obpg_bandpass_csv, parse_obpg_rsr_netcdf
from rsrf.validate import parse_manifest_dict


def _sampled_manifest_payload() -> dict:
    payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_sentinel2c_v2.json"))
    payload["source_id"] = "obpg_sampled_test"
    payload["sensor_unit_id"] = "orbview-2_seawifs"
    payload["title"] = "OBPG sampled parser test"
    payload["url"] = "https://oceancolor.gsfc.nasa.gov/resources/docs/rsr_tables/"
    payload["doc_version"] = "test"
    payload["raw_local_path"] = "sources/raw/test_obpg.nc"
    payload["file_sha256"] = "test"
    payload["parser"]["script"] = "scripts/ingest/ingest_sampled_curve.py"
    payload["parser"]["entrypoint"] = "parse_obpg_rsr_netcdf"
    payload["validation"]["plot_overlay_required"] = False
    payload["validation"]["expected_band_count"] = 2
    return payload


def _band_spec_manifest_payload() -> dict:
    payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json"))
    payload["source_id"] = "obpg_bandpass_test"
    payload["sensor_unit_id"] = "pace_oci"
    payload["representation_variant"] = "l1b_band_spec"
    payload["title"] = "OBPG bandpass parser test"
    payload["url"] = "https://oceancolor.gsfc.nasa.gov/data/pace/characterization/"
    payload["doc_version"] = "test"
    payload["raw_local_path"] = "sources/raw/test_obpg_bandpass.csv"
    payload["file_sha256"] = "test"
    payload["parser"]["script"] = "scripts/ingest/ingest_band_spec_table.py"
    payload["parser"]["entrypoint"] = "parse_obpg_bandpass_csv"
    payload["band_spec"]["band_index_field"] = "Band Number"
    payload["band_spec"]["band_id_field"] = None
    payload["band_spec"]["center_wavelength_field"] = "Center Wavelength"
    payload["band_spec"]["fwhm_field"] = "Width (FWHM)"
    payload["validation"]["expected_band_count"] = 2
    payload["validation"]["monotonic_centers_required"] = False
    payload["curve_realization"]["enabled"] = False
    payload["curve_realization"]["output_representation_variant"] = None
    payload["curve_realization"]["profile_type"] = None
    payload["curve_realization"]["approximation"] = False
    payload["curve_realization"]["approximation_reason"] = None
    payload["curve_realization"]["persist_realized_curves"] = False
    payload["curve_realization"]["grid_policy"] = None
    return payload


class ObpgParserTests(unittest.TestCase):
    def test_parse_obpg_rsr_netcdf_uses_band_coordinate_centers(self) -> None:
        manifest = parse_manifest_dict(_sampled_manifest_payload())
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_path = Path(tmpdir) / "fixture.nc"
            dataset = xr.Dataset(
                data_vars={
                    "wavelength": (("wavelengths",), np.asarray([400.0, 401.0, 402.0], dtype=np.float32)),
                    "RSR": (
                        ("bands", "wavelengths"),
                        np.asarray(
                            [[0.0, 1.0, 0.0], [-0.1, 0.5, 0.0]],
                            dtype=np.float32,
                        ),
                    ),
                },
                coords={
                    "bands": np.asarray([412.0, 443.0], dtype=np.float32),
                },
            )
            dataset.to_netcdf(dataset_path, engine="netcdf4")
            artifacts = parse_obpg_rsr_netcdf(dataset_path, manifest)

        self.assertEqual(len(artifacts.band_rows), 2)
        self.assertEqual(artifacts.band_rows[0]["band_id"], "B01")
        self.assertEqual(artifacts.band_rows[0]["center_wavelength_nm"], 412.0)
        self.assertEqual(artifacts.band_rows[1]["center_wavelength_nm"], 443.0)
        negative_row = next(
            row for row in artifacts.curve_rows if row["band_id"] == "B02" and row["wavelength_nm"] == 400.0
        )
        self.assertEqual(negative_row["response"], 0.0)

    def test_parse_obpg_bandpass_csv_skips_units_row(self) -> None:
        manifest = parse_manifest_dict(_band_spec_manifest_payload())
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = Path(tmpdir) / "fixture.csv"
            with table_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "Band Number",
                        "Nominal Center Wavelength (int)",
                        "Center Wavelength",
                        "Width (FWHM)",
                    ]
                )
                writer.writerow(["", "nm", "nm", "nm"])
                writer.writerow([1, 315, 314.55, 4.06])
                writer.writerow([2, 316, 316.239, 5.034])

            artifacts = parse_obpg_bandpass_csv(table_path, manifest)

        self.assertEqual(len(artifacts.band_spec_rows), 2)
        self.assertEqual(artifacts.band_spec_rows[0]["band_id"], "B01")
        self.assertAlmostEqual(artifacts.band_spec_rows[0]["center_wavelength_nm"], 314.55)
        self.assertAlmostEqual(artifacts.band_rows[1]["fwhm_nm"], 5.034)


if __name__ == "__main__":
    unittest.main()
