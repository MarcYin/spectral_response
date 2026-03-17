# RSRF

`RSRF` is a repository-backed Python toolkit for canonical optical sensor response definitions.

It is designed for workflows where the code and the curated spectral-response repository evolve together:

- ingest official sampled curves and band-parameter metadata
- normalize them into stable parquet-backed canonical forms
- inspect and validate sensor definitions from Python or the CLI
- publish documentation and package releases from CI
- keep manifests, source artifacts, and planning documents organized in a predictable layout

## Core concepts

- `sampled_curve`: a band has an explicit wavelength grid and response samples
- `band_spec`: a band has metadata such as center wavelength and FWHM, but not an official full sampled curve
- `realized_curve`: an optional derived approximation, typically Gaussian from `band_spec`

## What this repo covers today

- broad multispectral coverage across Sentinel, Landsat, MODIS, VIIRS, OLCI, ASTER, Planet, PROBA-V, and legacy ocean-colour families
- hyperspectral or metadata-driven band specs for PACE OCI, EnMAP, EMIT, PRISMA, Satellogic NewSat, and several public interval-metadata families
- registry-backed QA and validation exports

## What the package does not ship

The published Python package is intended to ship code, not the full repository data. Use `--root` or `RSRF_ROOT` to point the installed package at a checkout or generated data root.

Continue with [Getting Started](getting-started.md) or review the [Repository Layout](repository-layout.md).
