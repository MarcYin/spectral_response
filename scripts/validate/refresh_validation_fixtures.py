"""Refresh normalized validation-report regression fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.qa import validate_sensor

FIXTURES = ROOT / "tests" / "fixtures" / "validation_reports"
TARGETS = (
    ("sentinel-2c_msi", "band_average", "sentinel-2c_msi_band_average.json"),
    (
        "hyperspec_example",
        "metadata_band_spec",
        "hyperspec_example_metadata_band_spec.json",
    ),
)


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for sensor_unit_id, representation_variant, filename in TARGETS:
        report = validate_sensor(sensor_unit_id, representation_variant, root=ROOT)
        payload = _normalize_value(report)
        output_path = FIXTURES / filename
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(output_path)
    return 0


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
    raise SystemExit(main())
