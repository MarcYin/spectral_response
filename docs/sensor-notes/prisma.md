# PRISMA

## Status

Blocked as of 2026-03-17.

## Source Choice

- primary public entry point checked: <https://www.asi.it/en/earth-science/prisma/>
- current repo policy target: exact public per-band wavelength/FWHM metadata or a public sample product metadata artifact

## What Is Publicly Confirmed

- PRISMA is a VNIR/SWIR hyperspectral mission with a public ASI mission page
- public docs and ecosystem references indicate product metadata contains wavelength vectors

## Why It Is Still Blocked

- no reproducible public per-band wavelength/FWHM table has been staged in-repo yet
- no anonymous public sample product metadata artifact has been identified in this repo workflow
- mission-level summaries are not sufficient to fabricate a 200+ band canonical wavelength table

## Next Acceptable Promotion Path

- stage a public PRISMA sample product metadata artifact, or
- stage an official PRISMA technical table that lists the actual per-band wavelength/FWHM vectors

## Unresolved Caveat

- do not derive a full PRISMA band list from only total band counts, total wavelength span, or average spectral resolution
