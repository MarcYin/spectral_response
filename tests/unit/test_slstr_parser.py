from __future__ import annotations

import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.manifests import manifest_path
from rsrf.parsers.slstr import parse_slstr_nwp_saf_tar
from rsrf.validate import parse_manifest_dict


def _manifest_for(sensor_unit_id: str) -> dict:
    payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_sentinel2c_v2.json"))
    payload["source_id"] = f"{sensor_unit_id}_slstr_test"
    payload["sensor_unit_id"] = sensor_unit_id
    payload["title"] = f"{sensor_unit_id} SLSTR test source"
    payload["url"] = (
        "https://nwp-saf.eumetsat.int/site/software/rttov/download/coefficients/spectral-response-functions/"
    )
    payload["doc_version"] = "test"
    payload["raw_local_path"] = "sources/raw/test_slstr.tar.gz"
    payload["file_sha256"] = "test"
    payload["parser"]["script"] = "scripts/ingest/ingest_sampled_curve.py"
    payload["parser"]["entrypoint"] = "parse_slstr_nwp_saf_tar"
    payload["validation"]["plot_overlay_required"] = False
    payload["validation"]["expected_band_count"] = 11
    payload["validation"]["expected_domain"] = "VSWIR_TIR"
    return payload


class SlstrParserTests(unittest.TestCase):
    def test_parser_extracts_slstr_tar_and_adds_fire_bands(self) -> None:
        manifest = parse_manifest_dict(_manifest_for("sentinel-3a_slstr"))
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / "fixture.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                for channel in range(1, 10):
                    band_id = f"S{channel}"
                    text = self._sample_member_text(channel, band_id)
                    payload = text.encode("utf-8")
                    info = tarfile.TarInfo(name=f"rtcoef_sentinel3_1_slstr_srf_ch{channel:02d}.txt")
                    info.size = len(payload)
                    archive.addfile(info, io.BytesIO(payload))

            artifacts = parse_slstr_nwp_saf_tar(archive_path, manifest)

        band_ids = [row["band_id"] for row in artifacts.band_rows]
        self.assertEqual(band_ids, ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "F1", "F2"])
        self.assertEqual(artifacts.metadata["slstr_srf"]["derived_band_duplicates"], {"F1": "S7", "F2": "S8"})

        s1_rows = [row for row in artifacts.curve_rows if row["band_id"] == "S1"]
        self.assertEqual([row["wavelength_nm"] for row in s1_rows], [500.0, 1000.0, 2000.0])

        s7_rows = [row for row in artifacts.curve_rows if row["band_id"] == "S7"]
        f1_rows = [row for row in artifacts.curve_rows if row["band_id"] == "F1"]
        self.assertEqual(
            [(row["wavelength_nm"], row["response"]) for row in s7_rows],
            [(row["wavelength_nm"], row["response"]) for row in f1_rows],
        )

    @staticmethod
    def _sample_member_text(channel: int, band_id: str) -> str:
        return "\n".join(
            [
                f"{channel}, Resampled Sentinel-3A SLSTR {band_id} unpolarised FPA response at 87 K created 2015-01-22T17:20:15Z",
                "Number of data points:",
                "3",
                "Wavenumber (cm-1)   Filter response",
                "5000.000000 0.100000",
                "10000.000000 0.500000",
                "20000.000000 1.000000",
                "",
            ]
        )


if __name__ == "__main__":
    unittest.main()
