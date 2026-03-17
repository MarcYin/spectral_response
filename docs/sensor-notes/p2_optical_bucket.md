# P2 Optical Bucket

## Status

Planning catalog reduced to the remaining blocked family on 2026-03-17.

## Scope

The current planning-only optical backlog covers:

- `prisma_hsi`

## Promoted On 2026-03-17

The following P2 families were promoted from planning-only to canonical `band_spec` ingests using public official or WMO OSCAR interval metadata:

- `pleiades_msi`
- `pleiades-neo_msi`
- `spot-6_7_msi`
- `amazonia-1_optical_imager`
- `cbers-4a_optical_payload`:
  `mux_band_spec`, `wfi_band_spec`, `wpm_band_spec`
- `formosat-5_rsi`

## Why PRISMA Is Still Planning-Only

The original implementation plan explicitly marked P2 as registry-first and ingest-later. PRISMA remains planning-only because the public ASI pages confirm mission-level sensor characteristics but do not currently expose a reproducible public per-band wavelength/FWHM artifact that can be staged in-repo without authenticated product access.

## Current pattern

- public exact source still not staged: PRISMA
- future ingest should still prefer exact public band tables or product metadata over brochure-style summaries
- do not synthesize a PRISMA wavelength vector from brochure-level mission summaries

## Source entry points

- PRISMA: <https://www.asi.it/en/earth-science/prisma/>
- Current promoted interval-metadata sources:
  - WMO OSCAR instrument pages for Pleiades, Pleiades-Neo, SPOT-6/7, and FORMOSAT-5
  - INPE camera metadata pages for Amazonia-1 WFI and CBERS-4A MUX/WFI/WPM
