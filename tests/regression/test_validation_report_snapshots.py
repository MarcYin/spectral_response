from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.qa import validate_sensor

FIXTURES = ROOT / "tests" / "fixtures" / "validation_reports"


class ValidationReportSnapshotTests(unittest.TestCase):
    def test_sentinel2c_report_matches_fixture(self) -> None:
        self.assertEqual(
            _normalized_report("sentinel-2c_msi", "band_average"),
            _load_fixture("sentinel-2c_msi_band_average.json"),
        )

    def test_hyperspec_report_matches_fixture(self) -> None:
        self.assertEqual(
            _normalized_report("hyperspec_example", "metadata_band_spec"),
            _load_fixture("hyperspec_example_metadata_band_spec.json"),
        )


def _normalized_report(sensor_unit_id: str, representation_variant: str) -> dict[str, Any]:
    report = validate_sensor(sensor_unit_id, representation_variant, root=ROOT)
    return _normalize_value(report)


def _load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_value(item)
            for key, item in sorted(value.items())
            if key != "metadata_generated_at"
        }
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, float):
        return round(value, 6)
    return value


if __name__ == "__main__":
    unittest.main()
