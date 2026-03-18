"""Prepare generated docs files and visualization bundle assets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.docs_site import prepare_docs_site


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare generated MkDocs files and versioned visualization bundles.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root; defaults to the current repository",
    )
    parser.add_argument(
        "--skip-visualization-data",
        action="store_true",
        help="skip refreshing docs/assets/visualization JSON payloads",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    written = prepare_docs_site(
        args.root,
        refresh_visualization_data=not args.skip_visualization_data,
    )
    for label, path in written.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
