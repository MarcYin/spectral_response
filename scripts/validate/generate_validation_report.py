"""Generate a JSON validation report and overview plot for a sensor variant."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.qa import write_validation_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a validation report for a sensor variant.")
    parser.add_argument("sensor_unit_id")
    parser.add_argument(
        "--variant",
        dest="representation_variant",
        default=None,
        help="representation variant; required only when multiple variants exist",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root; defaults to the current workspace root",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="directory for validation_report.json and overview.png",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        written = write_validation_artifacts(
            args.sensor_unit_id,
            args.representation_variant,
            root=args.root,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError, NotImplementedError) as exc:
        print(str(exc))
        return 1

    for label, path in written.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
