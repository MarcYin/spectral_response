# Manifest Library

This directory groups manifest files by intent so the repository root stays clean.

- `official/`: checked-in source manifests that can be ingested
- `planning/`: planning catalogs that describe backlog sensors without canonical artifacts
- `templates/`: starter manifests for adding new sources

Most CLI and ingest flows accept either an explicit manifest path or just the manifest filename. Filename lookup resolves against this library.
