# Copyright and Attribution Notice

This repository combines original `oxidized-rasterstats` work with upstream
`python-rasterstats`-derived components.

## Original `oxidized-rasterstats` work

Unless otherwise noted, new implementation artifacts in this repository are
copyright:

- Copyright (c) 2026 Roger Lew

This includes the Rust implementation and project-specific artifacts such as:

- `src/*.rs` (Rust zonal/point/statistics/geometry/error modules and bridge code)
- `Cargo.toml` and Rust build integration
- `tests/regression/*`
- `tests/perf/*`
- `benchmarks/results/*`
- `scripts/build_weppcloud_fixtures.py`
- `scripts/generate_api_manifest.py`
- Repository-specific docs in `docs/` and `README.md`

## Upstream-derived components

Portions are derived from upstream `python-rasterstats` by Matthew Perry and
contributors, including compatibility-layer code, vendored snapshots, and
upstream-derived tests/fixtures.

- Copyright (c) 2013 Matthew Perry

Primary locations:

- `vendor/upstream_rasterstats/`
- `tests/upstream/`
- `tests/data/` (synced parity fixtures)
- `python/rasterstats/_upstream_main.py`
- `python/rasterstats/_upstream_point.py`
- `python/rasterstats/io.py`
- `python/rasterstats/utils.py`
- `python/rasterstats/cli.py`

Upstream license text is preserved in `vendor/upstream_rasterstats/LICENSE.txt`.

## License

This project is distributed under the BSD 3-Clause License. See `LICENSE`.
