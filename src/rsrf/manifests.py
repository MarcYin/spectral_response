"""Helpers for working with the repository's source manifest library."""

from __future__ import annotations

from pathlib import Path

from .registry import build_repo_layout

OFFICIAL_MANIFEST_DIRNAME = "official"
PLANNING_MANIFEST_DIRNAME = "planning"
TEMPLATE_MANIFEST_DIRNAME = "templates"


def source_manifest_root(root: Path | None = None) -> Path:
    """Return the root directory that contains all manifest groups."""

    return build_repo_layout(root).source_manifests_root


def official_manifest_root(root: Path | None = None) -> Path:
    """Return the directory for checked-in ingestable manifests."""

    return build_repo_layout(root).official_source_manifests_root


def planning_manifest_root(root: Path | None = None) -> Path:
    """Return the directory for planning-only manifest catalogs."""

    return build_repo_layout(root).planning_source_manifests_root


def template_manifest_root(root: Path | None = None) -> Path:
    """Return the directory for reusable manifest templates."""

    return build_repo_layout(root).template_source_manifests_root


def manifest_path(
    root: Path | None,
    filename: str,
    *,
    manifest_group: str = OFFICIAL_MANIFEST_DIRNAME,
) -> Path:
    """Return the canonical path for a manifest in the requested group."""

    layout = build_repo_layout(root)
    group_roots = {
        OFFICIAL_MANIFEST_DIRNAME: layout.official_source_manifests_root,
        PLANNING_MANIFEST_DIRNAME: layout.planning_source_manifests_root,
        TEMPLATE_MANIFEST_DIRNAME: layout.template_source_manifests_root,
    }
    if manifest_group not in group_roots:
        raise ValueError(f"unknown manifest group: {manifest_group}")
    return group_roots[manifest_group] / filename


def resolve_manifest_path(path_or_name: str | Path, root: Path | None = None) -> Path:
    """Resolve a manifest from an explicit path or a library filename.

    Resolved paths are validated to reside within the repository tree to
    prevent accidental loading of manifests from arbitrary locations.
    """

    layout = build_repo_layout(root)
    repo_root = layout.root

    candidate = Path(path_or_name).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved
        raise FileNotFoundError(f"manifest not found: {candidate}")

    cwd_candidate = candidate.resolve()
    if cwd_candidate.exists():
        _check_path_within_repo(cwd_candidate, repo_root, path_or_name)
        return cwd_candidate

    repo_relative = (repo_root / candidate).resolve()
    if repo_relative.exists():
        return repo_relative

    search_roots = (
        official_manifest_root(repo_root),
        planning_manifest_root(repo_root),
        template_manifest_root(repo_root),
    )
    for base_root in search_roots:
        library_candidate = base_root / candidate.name
        if library_candidate.exists():
            return library_candidate.resolve()

    raise FileNotFoundError(f"manifest not found: {path_or_name}")


def _check_path_within_repo(resolved: Path, repo_root: Path, original: str | Path) -> None:
    """Raise ValueError if *resolved* is outside the repository root."""
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        raise ValueError(
            f"manifest path {original} resolves to {resolved} which is outside the repository root {repo_root}"
        ) from None


def iter_source_manifest_paths(
    root: Path | None = None,
    *,
    include_templates: bool = False,
    include_planning: bool = False,
) -> tuple[Path, ...]:
    """Return the checked-in manifest files in stable sorted order."""

    roots = [official_manifest_root(root)]
    if include_planning:
        roots.append(planning_manifest_root(root))
    if include_templates:
        roots.append(template_manifest_root(root))

    paths: list[Path] = []
    for base_root in roots:
        if not base_root.exists():
            continue
        paths.extend(sorted(base_root.glob("*.json")))
    return tuple(paths)
