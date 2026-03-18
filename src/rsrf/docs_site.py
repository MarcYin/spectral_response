"""Helpers for preparing generated docs bundle files."""

from __future__ import annotations

import shutil
from pathlib import Path

from .registry import build_repo_layout
from .visualization import export_docs_visualization_assets

VISUALIZATION_BUNDLE_VERSION = "20260318-v1"
VISUALIZATION_BUILD_ID = VISUALIZATION_BUNDLE_VERSION
VISUALIZATION_TEMPLATE_PAGE = Path("docs/visualizations.md.template")
VISUALIZATION_PAGE = Path("docs/visualizations.md")
VISUALIZATION_JS_SOURCE = Path("docs/assets/javascripts/rsrf-visualizations.js")
VISUALIZATION_CSS_SOURCE = Path("docs/assets/stylesheets/rsrf-visualizations.css")
MKDOCS_TEMPLATE = Path("mkdocs.yml.template")
MKDOCS_CONFIG = Path("mkdocs.yml")


def visualization_js_bundle_filename() -> str:
    return f"rsrf-visualizations-{VISUALIZATION_BUNDLE_VERSION}.js"


def visualization_css_bundle_filename() -> str:
    return f"rsrf-visualizations-{VISUALIZATION_BUNDLE_VERSION}.css"


def prepare_docs_site(
    root: Path | None = None,
    *,
    refresh_visualization_data: bool = True,
) -> dict[str, Path]:
    """Render generated docs files and sync versioned visualization bundles."""

    layout = build_repo_layout(root)
    resolved_root = layout.root
    if refresh_visualization_data:
        export_docs_visualization_assets(resolved_root)

    js_target = resolved_root / "docs" / "assets" / "javascripts" / visualization_js_bundle_filename()
    css_target = resolved_root / "docs" / "assets" / "stylesheets" / visualization_css_bundle_filename()
    page_target = resolved_root / VISUALIZATION_PAGE
    mkdocs_target = resolved_root / MKDOCS_CONFIG

    _remove_stale_bundles(
        resolved_root / "docs" / "assets" / "javascripts",
        pattern="rsrf-visualizations-*.js",
        keep=js_target.name,
    )
    _remove_stale_bundles(
        resolved_root / "docs" / "assets" / "stylesheets",
        pattern="rsrf-visualizations-*.css",
        keep=css_target.name,
    )

    _render_template(
        resolved_root / VISUALIZATION_JS_SOURCE,
        js_target,
        {
            "__RSRF_VISUALIZATION_BUILD_ID__": VISUALIZATION_BUILD_ID,
        },
    )
    shutil.copyfile(resolved_root / VISUALIZATION_CSS_SOURCE, css_target)
    _render_template(
        resolved_root / VISUALIZATION_TEMPLATE_PAGE,
        page_target,
        {
            "__RSRF_VISUALIZATION_BUILD_ID__": VISUALIZATION_BUILD_ID,
        },
    )
    _render_template(
        resolved_root / MKDOCS_TEMPLATE,
        mkdocs_target,
        {
            "__RSRF_VISUALIZATION_JS_BUNDLE__": visualization_js_bundle_filename(),
            "__RSRF_VISUALIZATION_CSS_BUNDLE__": visualization_css_bundle_filename(),
        },
    )

    return {
        "mkdocs_config": mkdocs_target,
        "page": page_target,
        "js_bundle": js_target,
        "css_bundle": css_target,
        "visualization_data": resolved_root / "docs" / "assets" / "visualization",
    }


def _render_template(source_path: Path, target_path: Path, substitutions: dict[str, str]) -> None:
    contents = source_path.read_text(encoding="utf-8")
    for placeholder, value in substitutions.items():
        contents = contents.replace(placeholder, value)
    target_path.write_text(contents, encoding="utf-8")


def _remove_stale_bundles(directory: Path, *, pattern: str, keep: str) -> None:
    for path in directory.glob(pattern):
        if path.name != keep:
            path.unlink()
