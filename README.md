# Spectral Response Function Repository

This repository bootstraps a Python package and data layout for storing canonical spectral response definitions for satellite sensors.

The active design baseline is documented in:

- `rsrf_repo_plan_v3_hyperspectral_support.md`
- `rsrf_implementation_plan.md`

## Current status

The repository currently contains:

- a `src/rsrf/` package skeleton
- a CLI bootstrap for manifest validation and layout inspection
- placeholder ingest entrypoints for sampled-curve and band-spec workflows
- data, docs, scripts, sources, and tests directories aligned with the implementation plan

## Repository layout

```text
.
|-- data/
|   |-- canonical/
|   |-- common_grid/
|   |-- realized/
|   `-- registry/
|-- docs/
|   |-- decisions/
|   `-- sensor-notes/
|-- scripts/
|   |-- build/
|   |-- ingest/
|   `-- validate/
|-- sources/
|   |-- extracted/
|   |-- manifests/
|   `-- raw/
|-- src/rsrf/
|-- tests/
|   |-- fixtures/
|   |-- regression/
|   `-- unit/
`-- rsrf_*.md / rsrf_*.json planning artifacts
```

## Package modules

- `rsrf.models`: core enums and lightweight data classes
- `rsrf.registry`: repository path conventions
- `rsrf.io`: JSON and metadata helpers
- `rsrf.band_specs`: helpers for metadata-only band definitions
- `rsrf.realize`: Gaussian realization from center wavelength and FWHM
- `rsrf.resample`: linear resampling helpers
- `rsrf.convolve`: basic convolution helpers
- `rsrf.validate`: manifest validation and bootstrap checks
- `rsrf.plotting`: simple curve plotting helpers
- `rsrf.cli`: command-line entrypoints
- `rsrf.registry`: normalized registry row builders and table definitions

## Bootstrap commands

Without installing the package:

```bash
PYTHONPATH=src python3 -m rsrf --help
PYTHONPATH=src python3 -m rsrf show-layout
PYTHONPATH=src python3 -m rsrf validate-manifest rsrf_source_manifest_sentinel2c_v2.json
PYTHONPATH=src python3 -m rsrf show-registry-rows rsrf_source_manifest_hyperspectral_band_spec_example.json
PYTHONPATH=src python3 -m rsrf register-manifest rsrf_source_manifest_sentinel2c_v2.json
python3 scripts/ingest/ingest_sentinel2_srf.py --dry-run
python3 scripts/ingest/ingest_band_spec_table.py --dry-run
```

After installation:

```bash
rsrf --help
```

## Next implementation steps

1. Replace the ingest placeholders with real parsers.
2. Add structured registry table writes.
3. Add sensor-specific validation plots and regression fixtures.
4. Expand from the two reference sources to the wider P0 sensor set.
