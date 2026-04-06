# Releasing

## Package name

The configured PyPI distribution name is `RSRF`. Verify availability before the first publish if the project has not yet been registered on PyPI.

## Build locally

```bash
python3 -m pip install -e ".[dev]"
python3 -m build
python3 -m twine check dist/*
```

## GitHub Actions

This repo includes three workflows:

- `ci.yml`: lint checks (ruff), test matrix (Python 3.9–3.14), and packaging smoke check
- `docs.yml`: build and deploy MkDocs to GitHub Pages
- `release-package.yml`: build and publish to PyPI, then publish the runtime data bundle to the GitHub Release

## Trusted publishing setup

Before the first PyPI release:

1. Create the `RSRF` project on PyPI if needed.
2. Add this GitHub repository as a trusted publisher in PyPI.
3. Ensure GitHub Pages is configured to deploy from GitHub Actions.

## Release flow

Recommended release sequence:

1. Merge verified changes to `main`.
2. Wait for the `CI` workflow on `main` to finish successfully.
3. Create and push a version tag such as `v0.3.0`.
4. Let `release-package.yml` start automatically from that tag push and publish the package.
5. The same workflow uploads `rsrf-root-vX.Y.Z.tar.gz` to the GitHub Release so installed-package users can bootstrap the matching runtime data snapshot automatically.

If you prefer a dry run first, use the workflow's manual dispatch option.
