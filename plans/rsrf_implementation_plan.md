# RSRF implementation kickoff plan

## 1. Purpose

This document turns the architecture in `rsrf_repo_plan_v3_hyperspectral_support.md` into an implementation plan that can start immediately.

The goal of the first implementation cycle is not "ingest every sensor". The goal is to prove the repository, schema, parser contract, and QA flow with one sampled-curve source and one metadata-only band-spec source.

## 2. Adopted baseline

- Use `rsrf_repo_plan_v3_hyperspectral_support.md` as the active design baseline.
- Keep `rsrf_repo_plan_v2.md` as historical context only.
- Keep the v2 manifest examples only as references; all new work should target `rsrf_source_manifest_template_v2.json`.

## 3. MVP scope

The MVP is complete when the repository can:

1. validate a manifest
2. ingest a sampled-curve source into canonical storage
3. ingest a band-spec source into canonical storage
4. realize an approximate curve from a band spec on demand
5. run automated QA and produce a small validation report
6. expose a minimal Python API for discovery, loading, and convolution prep

The MVP does not need:

- all P0 sensors
- precomputed common-grid files for every sensor
- multiple approximation profiles beyond the first Gaussian realization path
- a polished public release process

## 4. Decisions to freeze before coding

These decisions should be treated as fixed for the first implementation pass.

### 4.1 Language and packaging

- Python 3.11
- package layout under `src/rsrf/`
- tests with `pytest`

### 4.2 Core dependencies

- `numpy` for numeric operations
- `pandas` plus `pyarrow` for tabular IO and parquet writing
- `pydantic` for manifest and metadata validation
- `xarray` plus `netCDF4` only for derived `common_grid` outputs
- `matplotlib` for QA plots
- `typer` for a thin CLI

### 4.3 Canonical storage contract

- canonical content kinds: `sampled_curve` and `band_spec`
- optional derived storage: `realized`
- `common_grid` stays derived and is not required for MVP completion

### 4.4 First two reference sources

- sampled-curve path: `rsrf_source_manifest_sentinel2c_v2.json`
- band-spec path: `rsrf_source_manifest_hyperspectral_band_spec_example.json`

This pair is enough to force both canonical forms, the validation split, and the realization path.

## 5. Proposed repository layout

The first implementation pass should create this structure:

```text
spectral_response_function/
  pyproject.toml
  README.md
  src/rsrf/
    __init__.py
    cli.py
    models.py
    registry.py
    io.py
    band_specs.py
    realize.py
    resample.py
    convolve.py
    validate.py
    plotting.py
  scripts/ingest/
    ingest_sentinel2_srf.py
    ingest_band_spec_table.py
  tests/
    unit/
    regression/
    fixtures/
  data/
    registry/
    canonical/
    realized/
    common_grid/
  docs/
    decisions/
    sensor-notes/
```

## 6. Implementation phases

### Phase 0 - bootstrap the repository

Deliverables:
- `pyproject.toml`
- package skeleton under `src/rsrf/`
- CLI entrypoint
- test skeleton
- top-level `README.md`

Acceptance criteria:
- environment installs cleanly
- `pytest` runs
- CLI help command runs

### Phase 1 - freeze the schema and parser contract

Deliverables:
- manifest model matching `rsrf_source_manifest_template_v2.json`
- metadata sidecar model
- registry table schemas for `sensors`, `bands`, `sources`, `band_specs`, and `realizations`
- shared writer and reader helpers

Acceptance criteria:
- both example manifests validate
- a parsed manifest can round-trip through the model without losing fields
- registry tables write and read from parquet without schema drift

### Phase 2 - build the validation layer

Deliverables:
- sampled-curve validators
- band-spec validators
- realization validators
- plotting helpers for overlay and per-band inspection

Acceptance criteria:
- validation failures are explicit and tied to sensor, variant, and band
- QA plots can be produced from both canonical forms

### Phase 3 - implement the sampled-curve vertical slice

Target source:
- Sentinel-2C MSI sampled SRF workbook

Deliverables:
- `scripts/ingest/ingest_sentinel2_srf.py`
- canonical `curves.parquet`
- metadata sidecar
- band summary extraction for `bands.parquet`
- regression fixture and parser test

Acceptance criteria:
- 13 bands are emitted
- wavelengths are monotonic within each band
- responses are finite and non-negative
- center and FWHM checks pass against source metadata

### Phase 4 - implement the band-spec vertical slice

Target source:
- hyperspectral band-spec example manifest

Deliverables:
- `scripts/ingest/ingest_band_spec_table.py`
- canonical `band_specs.parquet`
- metadata sidecar
- lazy `gaussian_from_fwhm` realization path
- realization validation test

Acceptance criteria:
- band indices are unique
- center wavelength and FWHM fields are preserved exactly
- realized curves recover source center and FWHM within tolerance
- approximation metadata is emitted for realized Gaussian curves

### Phase 5 - expose the minimal public API

Deliverables:
- `list_sensors()`
- `list_bands()`
- `load_response_definition()`
- `load_curve()`
- `load_band_spec()`
- `realize_curve()`
- `convolution_weights()`

Acceptance criteria:
- both reference sources can be discovered and loaded from the same API
- convolution weights accept either canonical form

### Phase 6 - expand beyond the reference sources

Order:
1. Sentinel-2A and Sentinel-2B
2. Landsat family
3. MODIS Terra/Aqua
4. VIIRS SNPP / NOAA-20 / NOAA-21
5. Sentinel-3 OLCI and ASTER

Rule:
- do not add a new family until the previous ingest is covered by parser tests and validation output

## 7. Immediate backlog

These are the first tasks to execute in order.

1. Initialize the repository and package skeleton.
2. Add the manifest and registry models.
3. Add parquet read/write helpers and metadata sidecar helpers.
4. Add the CLI commands:
   - `validate-manifest`
   - `ingest`
   - `validate-sensor`
5. Add validation functions for sampled curves and band specs.
6. Implement the Sentinel-2C parser.
7. Implement the generic band-spec parser.
8. Implement `realize_curve()` with Gaussian-from-FWHM support.
9. Add regression tests for both reference ingests.
10. Add README usage examples and the first decision log entries.

## 8. Risks and controls

### Risk 1 - source heterogeneity breaks the parser contract

Control:
- keep parser outputs strict
- let per-source parsers adapt inputs, not the shared storage format

### Risk 2 - approximation logic leaks into canonical storage

Control:
- store approximations only in `realized/`
- require `approximation` and `approximation_reason` on realized outputs

### Risk 3 - common-grid generation becomes a distraction

Control:
- defer bulk `common_grid` generation until both reference vertical slices are stable

### Risk 4 - too many sensors are attempted too early

Control:
- finish Sentinel-2C plus one band-spec source before expanding the ingest queue

## 9. Definition of implementation-ready

The project is ready to begin coding when the following are true:

- this kickoff plan is accepted
- the v3 architecture doc is the active baseline
- the first two reference manifests are accepted as the initial targets
- the team agrees not to expand sensor coverage before the two reference vertical slices pass QA
