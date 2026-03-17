# PRISMA

## Status

Implemented as of 2026-03-17 from a compact metadata-only HE5 extracted from a staged official L1 granule.

## Source Choice

- primary public entry point checked: <https://www.asi.it/en/earth-science/prisma/>
- public registration system checked: <https://prismauserregistration.asi.it/>
- public toolbox distribution checked: <https://earthbit-support.planetek.it/>
- staged source artifact: `sources/raw/asi/prisma/hsi/l1/std/offl/20190710/PRS_L1_STD_OFFL_20190710091734_20190710091738_0001_metadata.he5`
- current repo policy outcome: exact per-product wavelength/FWHM metadata extracted from an official HE5 granule into a compact reproducible metadata snapshot

## What Is Implemented

- the staged metadata snapshot exposes the root-level metadata vectors copied from the official granule:
  - `List_Cw_Vnir`
  - `List_Cw_Swir`
  - `List_Fwhm_Vnir`
  - `List_Fwhm_Swir`
- canonical ingest uses those arrays directly and excludes invalid non-positive placeholder slots
- the staged metadata snapshot yields `66` valid VNIR rows and `172` valid SWIR rows for `238` canonical band-spec entries
- the combined canonical ordering is `VNIR` then `SWIR` in native slot order, with subsystem and subsystem-band index preserved in `shape_param_json`
- Gaussian realized curves remain optional derived products; no sampled native SRF curves are claimed from this source

## Important Caveat

- this source is exact official product metadata for one granule, packaged as a compact HE5 metadata extract rather than the full source product
- product-level wavelength and FWHM vectors should still be preferred for scene-specific analysis when multiple PRISMA products are available
- the source metadata contains one trailing zero-valued SWIR placeholder slot, so the canonical band count is `238` instead of the nominal `66 + 174`

## Checked Public Sources

- mission page: <https://www.asi.it/en/earth-science/prisma/>
- mission presentation PDF: <https://www.asi.it/wp-content/uploads/2021/02/PRISMA-Mission-Status-v1f-1.pdf>
- toolbox host: <https://earthbit-support.planetek.it/>
- macOS toolbox disk image: <https://earthbit-support.planetek.it/macos/EarthBit-1.14.5-Darwin.dmg>
- Windows toolbox installer: <https://earthbit-support.planetek.it/windows/PrismaToolbox_1.0.0_setup.exe>
- registration system: <https://prismauserregistration.asi.it/>
- data-license PDF: <https://prismauserregistration.asi.it/LICENCE_TO_USE_PRISMA_DATA.pdf>
