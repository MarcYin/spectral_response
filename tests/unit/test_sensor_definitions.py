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

from rsrf import (
    SensorDefinitionValidationError,
    coerce_sensor_definition,
    dump_sensor_definition,
    get_sensor_definition,
    list_sensor_definitions,
    load_sensor_definition,
    sensor_definition_from_dict,
    sensor_definition_to_dict,
)


def _custom_sensor_payload() -> dict[str, object]:
    return {
        "schema_type": "rsrf_sensor_definition",
        "schema_version": "1.0.0",
        "sensor_id": "custom_example_sensor",
        "extensions": {
            "custom_consumer": {
                "mode": "reflectance",
                "revisions": [1, 2],
            }
        },
        "bands": [
            {
                "band_id": "blue",
                "response_definition": {
                    "kind": "gaussian",
                    "center_wavelength_nm": 490.0,
                    "fwhm_nm": 65.0,
                },
                "extensions": {
                    "spectral_library": {
                        "segment": "vnir",
                    }
                },
            },
            {
                "band_id": "swir1",
                "response_definition": {
                    "kind": "sampled",
                    "wavelength_nm": [1550.0, 1600.0, 1650.0],
                    "response": [0.1, 1.0, 0.1],
                },
                "extensions": {
                    "spectral_library": {
                        "segment": "swir",
                    },
                    "custom_consumer": {
                        "notes": ["primary"],
                    },
                },
            },
        ],
    }


class SensorDefinitionTests(unittest.TestCase):
    def test_sensor_definition_round_trips_extensions_through_dict(self) -> None:
        payload = _custom_sensor_payload()

        sensor_definition = sensor_definition_from_dict(payload)
        serialized = sensor_definition_to_dict(sensor_definition)

        self.assertEqual(serialized, payload)

    def test_load_and_dump_sensor_definition_round_trip_json(self) -> None:
        payload = _custom_sensor_payload()
        sensor_definition = sensor_definition_from_dict(payload)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sensor_definition.json"
            dump_sensor_definition(sensor_definition, path)
            loaded = load_sensor_definition(path)

        self.assertEqual(sensor_definition_to_dict(loaded), payload)

    def test_coerce_sensor_definition_accepts_json_path(self) -> None:
        payload = _custom_sensor_payload()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sensor_definition.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            sensor_definition = coerce_sensor_definition(path)

        self.assertEqual(sensor_definition.sensor_id, "custom_example_sensor")
        self.assertEqual(sensor_definition.bands[1].extensions["spectral_library"]["segment"], "swir")

    def test_coerce_sensor_definition_rejects_missing_json_path(self) -> None:
        with self.assertRaises(FileNotFoundError):
            coerce_sensor_definition("missing_sensor_definition.json", root=ROOT)

    def test_get_sensor_definition_normalizes_sampled_curve_sensor(self) -> None:
        sensor_definition = get_sensor_definition("sentinel-2c_msi", root=ROOT)

        self.assertEqual(sensor_definition.sensor_id, "sentinel-2c_msi")
        self.assertEqual(sensor_definition.schema_type, "rsrf_sensor_definition")
        self.assertEqual(sensor_definition.schema_version, "1.0.0")
        self.assertEqual(sensor_definition.bands[0].response_definition["kind"], "sampled")
        self.assertGreater(len(sensor_definition.bands[0].response_definition["wavelength_nm"]), 10)
        self.assertEqual(sensor_definition.bands[0].extensions, {})
        self.assertEqual(sensor_definition.extensions["rsrf"]["representation_variant"], "band_average")

    def test_get_sensor_definition_normalizes_band_spec_sensor(self) -> None:
        sensor_definition = get_sensor_definition("hyperspec_example", root=ROOT)

        self.assertEqual(sensor_definition.sensor_id, "hyperspec_example")
        self.assertEqual(sensor_definition.bands[0].response_definition["kind"], "gaussian")
        self.assertEqual(sensor_definition.bands[0].response_definition["center_wavelength_nm"], 410.0)
        self.assertEqual(sensor_definition.bands[0].extensions, {})
        self.assertEqual(sensor_definition.extensions["rsrf"]["representation_variant"], "metadata_band_spec")

    def test_get_sensor_definition_defaults_deterministically_for_multi_variant_sensor(self) -> None:
        sensor_definition = get_sensor_definition("probav_vgt", root=ROOT)

        self.assertEqual(sensor_definition.sensor_id, "probav_vgt")
        self.assertEqual(sensor_definition.extensions["rsrf"]["representation_variant"], "center_camera")

    def test_list_sensor_definitions_returns_known_sensor_ids(self) -> None:
        sensor_ids = list_sensor_definitions(root=ROOT)

        self.assertIn("sentinel-2c_msi", sensor_ids)
        self.assertIn("hyperspec_example", sensor_ids)

    def test_sensor_definition_rejects_duplicate_band_id(self) -> None:
        payload = _custom_sensor_payload()
        payload["bands"] = [payload["bands"][0], payload["bands"][0]]

        with self.assertRaises(SensorDefinitionValidationError) as context:
            sensor_definition_from_dict(payload)
        self.assertTrue(any("duplicates" in error for error in context.exception.errors))

    def test_sensor_definition_rejects_missing_spectral_library_segment(self) -> None:
        payload = _custom_sensor_payload()
        payload["bands"][0]["extensions"]["spectral_library"] = {}

        with self.assertRaises(SensorDefinitionValidationError) as context:
            sensor_definition_from_dict(payload)
        self.assertTrue(any("segment is required" in error for error in context.exception.errors))

    def test_sensor_definition_rejects_invalid_spectral_library_segment(self) -> None:
        payload = _custom_sensor_payload()
        payload["bands"][0]["extensions"]["spectral_library"]["segment"] = "thermal"

        with self.assertRaises(SensorDefinitionValidationError) as context:
            sensor_definition_from_dict(payload)
        self.assertTrue(any("must be one of" in error for error in context.exception.errors))

    def test_sensor_definition_rejects_invalid_sampled_curve(self) -> None:
        payload = _custom_sensor_payload()
        payload["bands"][1]["response_definition"]["response"] = [0.0, 0.0, 0.0]

        with self.assertRaises(SensorDefinitionValidationError) as context:
            sensor_definition_from_dict(payload)
        self.assertTrue(any("positive value" in error for error in context.exception.errors))


if __name__ == "__main__":
    unittest.main()
