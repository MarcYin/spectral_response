# P2 Optical Bucket

## Status

Planning catalog cleared on 2026-03-17.

## Scope

The current planning-only optical backlog is empty.

## Promoted On 2026-03-17

The following P2 families were promoted from planning-only to canonical `band_spec` ingests using public official or WMO OSCAR interval metadata:

- `pleiades_msi`
- `pleiades-neo_msi`
- `spot-6_7_msi`
- `amazonia-1_optical_imager`
- `cbers-4a_optical_payload`:
  `mux_band_spec`, `wfi_band_spec`, `wpm_band_spec`
- `formosat-5_rsi`
- `prisma_hsi`

## PRISMA Promotion

PRISMA moved out of the planning catalog once an official local HE5 granule was staged and distilled into a compact metadata-only HE5 snapshot for reproducible ingest. The ingest uses the exact `List_Cw_*` and `List_Fwhm_*` attributes from that source rather than brochure summaries or screenshot digitization.

## Current pattern

- planning catalog currently empty for the original P2 optical bucket
- PRISMA ingest now uses exact official product metadata from a staged local metadata extract
- future additions should still prefer exact official band tables or product metadata over brochure-style summaries
- do not synthesize dense hyperspectral wavelength vectors from only band counts, span, or average spectral resolution

## Source entry points

- PRISMA: <https://www.asi.it/en/earth-science/prisma/>
- PRISMA registration: <https://prismauserregistration.asi.it/>
- PRISMA toolbox host: <https://earthbit-support.planetek.it/>
- Current promoted interval-metadata sources:
  - WMO OSCAR instrument pages for Pleiades, Pleiades-Neo, SPOT-6/7, and FORMOSAT-5
  - INPE camera metadata pages for Amazonia-1 WFI and CBERS-4A MUX/WFI/WPM
