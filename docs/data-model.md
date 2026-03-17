# Data Model

## Canonical forms

RSRF stores optical response definitions in two canonical forms.

## `sampled_curve`

Use `sampled_curve` when the official source publishes explicit response samples on a wavelength axis.

Typical artifacts:

- `curves.parquet`
- `metadata.json`

Typical examples:

- Sentinel-2 MSI
- Landsat OLI/TIRS
- MODIS
- VIIRS
- Planet RSR CSV families

## `band_spec`

Use `band_spec` when the official source only publishes band parameters such as:

- center wavelength
- FWHM
- support interval
- quality flags

Typical artifacts:

- `band_specs.parquet`
- `metadata.json`

Typical examples:

- EnMAP
- EMIT
- PRISMA
- PACE OCI
- WMO OSCAR support-range proxies

## Realized curves

Some `band_spec` sources can optionally produce derived sampled curves under `data/realized/`. These are approximations, not replacements for native published SRFs.

## Registry tables

The repository registry lives under `data/registry/`:

- `sensors.parquet`
- `bands.parquet`
- `sources.parquet`
- `band_specs.parquet`
- `realizations.parquet`

These tables drive the public read API and the CLI.

## Repository root resolution

Repository-aware operations resolve the root in this order:

1. explicit `root=` argument or `--root`
2. `RSRF_ROOT`
3. upward search from the current working directory
