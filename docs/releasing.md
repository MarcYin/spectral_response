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
- `release-package.yml`: build and publish to PyPI using trusted publishing

## Trusted publishing setup

Before the first PyPI release:

1. Create the `RSRF` project on PyPI if needed.
2. Add this GitHub repository as a trusted publisher in PyPI.
3. Ensure GitHub Pages is configured to deploy from GitHub Actions.

## Release flow

Recommended release sequence:

1. Merge verified changes to `main`.
2. Wait for the `CI` workflow on `main` to finish successfully.
3. Create and push a version tag such as `v0.2.0`.
4. Let `release-package.yml` start automatically from that tag push and publish the package.
5. Create a GitHub Release from that tag if you want release notes on GitHub.

If you prefer a dry run first, use the workflow's manual dispatch option.
