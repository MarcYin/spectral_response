# DESIS

## Status

Not ingested yet.

## Current blocker

As of 2026-03-16, the public DESIS STAC item for `DESIS_HSI_L2A` exposes scene-level metadata and asset URLs, but it does not expose a public per-band wavelength/FWHM table in the STAC payload itself.

The `METADATA.xml` asset URL discovered from the public STAC item currently redirects to the DLR login flow when fetched anonymously, so it is not usable as a reproducible public raw source for this repository.

## Why this is not approximated here

Workshop and overview materials describe DESIS at the mission level, but they do not provide an exact public per-band band-center/FWHM table. This repository treats spectral response metadata as scientific source data, so approximate band grids are not being backfilled silently.

## Required source to unblock

One of the following public official artifacts is needed:

- a DESIS metadata XML product file that can be fetched anonymously and contains per-band wavelength/FWHM arrays
- a public DLR or NASA table with exact band centers and FWHM values
- an official STAC extension payload that exposes the per-band metadata directly
