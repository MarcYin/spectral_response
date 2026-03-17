# Repository Layout

`RSRF` separates code, curated data, source artifacts, and planning documents so users can find the right layer quickly.

## Top-level structure

```text
.
|-- data/
|-- docs/
|-- plans/
|-- scripts/
|-- sources/
|-- src/rsrf/
`-- tests/
```

## What lives where

- `data/canonical/`: canonical sampled curves and band specs written by ingest
- `data/realized/`: optional derived sampled curves for metadata-only sources
- `data/registry/`: parquet registries for sensors, bands, sources, band specs, and realizations
- `docs/`: MkDocs source for the user-facing documentation site
- `plans/`: implementation history and architecture planning
- `scripts/ingest/`: operator entrypoints for source ingest
- `scripts/validate/`: operator entrypoints for validation exports and fixture refresh
- `sources/raw/`: archived upstream source files
- `sources/extracted/`: reviewed extraction intermediates and trusted overlays
- `sources/manifests/official/`: checked-in source manifests used for ingest
- `sources/manifests/planning/`: backlog catalogs that register planned sensors
- `sources/manifests/templates/`: starter manifests for new sources
- `src/rsrf/commands/`: CLI parser, dispatch, and rendering helpers
- `src/rsrf/parsers/`: sensor-family-specific parser implementations
- `tests/unit/`: unit coverage for APIs, parsers, CLI, and registry behavior
- `tests/regression/`: validation-report snapshot regression tests

## Package map

Within `src/rsrf/`, the package is organized by responsibility:

- `api.py`: read-side access to canonical response definitions
- `commands/`: command-line interface implementation
- `convolve.py`, `resample.py`, `realize.py`: response processing helpers
- `ingest.py`: artifact writing and registry updates
- `manifests.py`: manifest lookup and path resolution
- `models.py`: typed data structures and manifest schema
- `planning.py`: planning-catalog helpers
- `qa.py`, `plotting.py`: validation logic and export plots
- `registry.py`, `io.py`: repository layout and parquet/JSON IO helpers

## Manifest resolution

Manifest-aware commands do not require long paths. When you pass a filename like `rsrf_source_manifest_sentinel2c_v2.json`, `RSRF` resolves it against `sources/manifests/official/`, then `planning/`, then `templates/`.
