# ADR-0001: Canonical Split Between `sampled_curve` and `band_spec`

## Status

Accepted.

## Context

Official optical sensor sources do not publish the same level of spectral detail.

Some sources publish full sampled response curves. Others publish only:

- center wavelength
- FWHM
- support interval
- quality flags

Treating both as the same canonical object would either lose precision for sampled data or fabricate detail for metadata-only sources.

## Decision

RSRF stores two canonical forms:

- `sampled_curve` for official wavelength/response samples
- `band_spec` for official metadata-only band definitions

Derived sampled approximations remain optional and are tracked separately as realizations.

## Consequences

- ingest pipelines stay honest about source fidelity
- APIs can dispatch by content kind without hiding approximations
- QA can apply different checks to exact curves and metadata-only definitions
- downstream users can choose whether to accept realized approximations
