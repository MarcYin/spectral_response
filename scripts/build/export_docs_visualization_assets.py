"""Export interactive visualization assets for the MkDocs site."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.visualization import export_docs_visualization_assets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export interactive spectral-response visualization assets for docs.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root; defaults to the current repository",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="override the docs visualization asset directory",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    written = export_docs_visualization_assets(
        args.root,
        output_dir=args.output_dir,
    )
    for label, path in written.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
