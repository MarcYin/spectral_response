# Spectral Response Function Repository

This repository bootstraps a Python package and data layout for storing canonical spectral response definitions for satellite sensors.

The active design baseline is documented in:

- `rsrf_repo_plan_v3_hyperspectral_support.md`
- `rsrf_implementation_plan.md`

## Current status

The repository currently contains:

- a registry-backed read API for canonical sampled curves and band specs
- a CLI for repository inspection, manifest validation, and canonical data discovery
- working ingest entrypoints for sampled-curve and band-spec workflows
- a shared `realize_curve()` helper used by runtime convolution and persisted realization
- optional persisted realized curves for band-spec sources under `data/realized/`
- regression fixtures for the reference validation reports
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

- `rsrf.api`: registry-backed read API for canonical curves and band specs
- `rsrf.models`: core enums and lightweight data classes
- `rsrf.registry`: repository path conventions
- `rsrf.io`: JSON and metadata helpers
- `rsrf.band_specs`: helpers for metadata-only band definitions
- `rsrf.realize`: Gaussian realization from center wavelength and FWHM
- `rsrf.resample`: linear resampling helpers
- `rsrf.convolve`: basic convolution helpers
- `rsrf.validate`: manifest validation and bootstrap checks
- `rsrf.qa`: sensor-level validation reports and QA artifact export
- `rsrf.plotting`: simple curve plotting helpers
- `rsrf.cli`: command-line entrypoints
- `rsrf.registry`: normalized registry row builders and table definitions

## Bootstrap commands

Without installing the package:

```bash
PYTHONPATH=src python3 -m rsrf --help
PYTHONPATH=src python3 -m rsrf show-layout
PYTHONPATH=src python3 -m rsrf list-sensors
PYTHONPATH=src python3 -m rsrf list-bands sentinel-2c_msi --variant band_average
PYTHONPATH=src python3 -m rsrf show-metadata hyperspec_example --variant metadata_band_spec
PYTHONPATH=src python3 -m rsrf show-response sentinel-2c_msi B03 --variant band_average
PYTHONPATH=src python3 -m rsrf validate-manifest rsrf_source_manifest_sentinel2c_v2.json
PYTHONPATH=src python3 -m rsrf show-registry-rows rsrf_source_manifest_hyperspectral_band_spec_example.json
PYTHONPATH=src python3 -m rsrf register-manifest rsrf_source_manifest_sentinel2c_v2.json
python3 scripts/ingest/ingest_sentinel2_srf.py --dry-run
python3 scripts/ingest/ingest_band_spec_table.py --dry-run
python3 scripts/validate/generate_validation_report.py sentinel-2c_msi --variant band_average
python3 scripts/validate/generate_validation_report.py hyperspec_example --variant metadata_band_spec
python3 scripts/validate/refresh_validation_fixtures.py
PYTHONPATH=src python3 - <<'PY'
from rsrf import list_sensors, load_response_definition, validate_sensor
print(list_sensors())
print(type(load_response_definition('sentinel-2c_msi', 'B01', 'band_average')).__name__)
print(validate_sensor('hyperspec_example', 'metadata_band_spec')['passed'])
PY
```

After installation:

```bash
rsrf --help
```

## Next implementation steps

1. Expand from the two reference sources to the wider P0 sensor set.
2. Add source-overlay validation when a trusted reference figure or alternate published curve is available.
