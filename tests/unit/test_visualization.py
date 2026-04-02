from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.visualization import export_docs_visualization_assets


class VisualizationExportTests(unittest.TestCase):
    def test_export_docs_visualization_assets_writes_index_and_sensor_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir).resolve()
            written = export_docs_visualization_assets(
                ROOT,
                output_dir=output_dir,
                sensor_keys={
                    ("sentinel-2c_msi", "band_average"),
                    ("hyperspec_example", "metadata_band_spec"),
                },
            )

            self.assertEqual(written["index"], output_dir / "index.json")
            self.assertEqual(written["overlap_index"], output_dir / "overlap_index.json")
            self.assertEqual(written["sensor_dir"], output_dir / "sensors")

            index_payload = read_json(output_dir / "index.json")
            overlap_payload = read_json(output_dir / "overlap_index.json")
            self.assertEqual(len(index_payload["sensors"]), 2)
            self.assertEqual(index_payload["heatmap"]["default_mode"], "no_pan")
            self.assertEqual(len(index_payload["heatmap"]["z"]), 2)
            self.assertEqual(len(index_payload["heatmap"]["modes"]["all_bands"]["z"]), 2)
            self.assertEqual(len(index_payload["heatmap"]["modes"]["no_pan"]["z"]), 2)
            self.assertEqual(len(overlap_payload["sensors"]), 2)
            self.assertNotIn("generated_at", index_payload)
            self.assertNotIn("generated_at", overlap_payload)
            self.assertNotIn("root", index_payload)
            self.assertNotIn("root", overlap_payload)
            self.assertNotIn("bands", index_payload["sensors"][0])
            self.assertIn("bands", overlap_payload["sensors"][0])

            sensor_files = {row["sensor_file"] for row in index_payload["sensors"]}
            self.assertIn("sensors/sentinel-2c_msi__band_average.json", sensor_files)
            self.assertIn("sensors/hyperspec_example__metadata_band_spec.json", sensor_files)

            sentinel_payload = read_json(output_dir / "sensors" / "sentinel-2c_msi__band_average.json")
            hyperspec_payload = read_json(output_dir / "sensors" / "hyperspec_example__metadata_band_spec.json")

            self.assertEqual(sentinel_payload["band_count"], 13)
            self.assertEqual(sentinel_payload["curve_origin"], "sampled_curve")
            self.assertGreater(len(sentinel_payload["bands"][0]["points"]), 10)

            self.assertEqual(hyperspec_payload["curve_origin"], "realized_band_spec")
            self.assertEqual(hyperspec_payload["band_count"], 6)
            self.assertEqual(
                hyperspec_payload["bands"][0]["curve_origin"],
                "realized_band_spec",
            )
            self.assertIn("is_pan_band", sentinel_payload["bands"][0])

    def test_export_docs_visualization_assets_tracks_pan_heatmap_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir).resolve()
            export_docs_visualization_assets(
                ROOT,
                output_dir=output_dir,
                sensor_keys={("landsat-8_oli", "band_average")},
            )

            index_payload = read_json(output_dir / "index.json")
            sensor_payload = read_json(output_dir / "sensors" / "landsat-8_oli__band_average.json")

            self.assertEqual(sensor_payload["pan_band_count"], 1)
            self.assertTrue(any(band["is_pan_band"] for band in sensor_payload["bands"]))
            self.assertNotEqual(
                index_payload["heatmap"]["modes"]["all_bands"]["z"][0],
                index_payload["heatmap"]["modes"]["no_pan"]["z"][0],
            )

    def test_export_docs_visualization_assets_is_stable_for_identical_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir).resolve()
            kwargs = {
                "output_dir": output_dir,
                "sensor_keys": {
                    ("sentinel-2c_msi", "band_average"),
                    ("hyperspec_example", "metadata_band_spec"),
                },
            }
            export_docs_visualization_assets(ROOT, **kwargs)
            first_index = (output_dir / "index.json").read_text(encoding="utf-8")
            first_overlap = (output_dir / "overlap_index.json").read_text(encoding="utf-8")
            first_sensor = (output_dir / "sensors" / "sentinel-2c_msi__band_average.json").read_text(encoding="utf-8")

            export_docs_visualization_assets(ROOT, **kwargs)

            self.assertEqual((output_dir / "index.json").read_text(encoding="utf-8"), first_index)
            self.assertEqual(
                (output_dir / "overlap_index.json").read_text(encoding="utf-8"),
                first_overlap,
            )
            self.assertEqual(
                (output_dir / "sensors" / "sentinel-2c_msi__band_average.json").read_text(encoding="utf-8"),
                first_sensor,
            )


if __name__ == "__main__":
    unittest.main()
