"""Register the planned P2 optical sensor bucket into the sensor registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.planning import register_planned_sensor_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Register the planned P2 optical sensor bucket into data/registry/sensors.parquet.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root; defaults to the current repository",
    )
    parser.add_argument(
        "--catalog-path",
        type=Path,
        default=None,
        help="override the planning catalog path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        written = register_planned_sensor_catalog(args.root, catalog_path=args.catalog_path)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    if written is None:
        print("No planned sensor rows were written.")
        return 0

    print(f"sensors: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
