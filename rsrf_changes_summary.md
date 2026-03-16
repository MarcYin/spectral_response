# RSRF changes summary

## Main changes from the uploaded plan and manifest

1. Canonical data is no longer limited to sampled SRF curves.
   - Added first-class canonical `band_spec` support for sources that only publish wavelength-grid and FWHM metadata.
   - This is the key change needed for hyperspectral sensors.

2. The storage model now has three layers instead of two.
   - `canonical`: source-native truth (`sampled_curve` or `band_spec`)
   - `realized`: optional sampled curves generated from canonical band specs
   - `common_grid`: convenience grids for downstream use

3. Approximation labeling moved to the right place.
   - A source-published band specification is not itself an approximation.
   - A Gaussian or other assumed profile generated from center/FWHM is a derived approximation and is labeled as such.

4. The schema now supports metadata-only hyperspectral sensors.
   - Added `content_kind`
   - Added `band_specs.parquet`
   - Added `realizations.parquet`
   - Added `band_index`, `band_status`, and `published_shape_type`

5. The API is no longer curve-only.
   - Added `load_response_definition(...)`
   - Added `load_band_spec(...)`
   - Added `realize_curve(...)`
   - Recommended that convolution accept either a sampled curve or a band spec

6. Validation is now split by canonical form.
   - Separate checks for sampled curves
   - Separate checks for band specifications
   - Added realized-curve QA for center/FWHM recovery

7. The manifest format is now explicit about source content.
   - Added `content_kind`
   - Added `canonical` section
   - Added `band_spec` section
   - Added `curve_realization` section
   - Added parser output declarations

## New artifacts

- `rsrf_repo_plan_v3_hyperspectral_support.md`
- `rsrf_source_manifest_template_v2.json`
- `rsrf_source_manifest_sentinel2c_v2.json`
- `rsrf_source_manifest_hyperspectral_band_spec_example.json`
