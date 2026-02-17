# oxidized-rasterstats

Rust-accelerated, GDAL-backed implementation of `rasterstats` with drop-in Python API compatibility.

## Status

- Import path compatibility: `from rasterstats import zonal_stats, point_query`
- Build/packaging flow: `maturin`
- Rust fast paths: zonal stats + point query
- Python fallback: upstream-compatible behavior preserved
- Non-overlap `nodata` semantics: matches upstream `python-rasterstats` boundless footprint behavior
- Rust dispatch exceptions are logged before fallback so backend failures are visible in operations logs

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e ".[test,perf]"
pip install maturin

python scripts/sync_upstream.py \
  --repo /workdir/python-rasterstats \
  --sha e51b48a62e3ac7e4ef4a81a8c2a8e5b90fa5e8ac

maturin develop --release
```

## Dispatch Model

- Default mode enables Rust fast-path for eligible `zonal_stats` and `point_query` calls.
- Set `OXRS_DISABLE_RUST=1` to force Python fallback behavior.
- Fast path auto-falls back to Python for unsupported dynamic cases.

Examples:

```bash
# Default mode (zonal fast path active when eligible)
PYTHONPATH=python python -c "from rasterstats import zonal_stats; print(callable(zonal_stats))"

# Force Python fallback for both APIs
PYTHONPATH=python OXRS_DISABLE_RUST=1 python -c "from rasterstats import point_query; print(point_query('POINT(245309 1000064)','tests/upstream/data/slope.tif')[0])"

# Explicit Rust-on flag is optional (kept for compatibility)
PYTHONPATH=python OXRS_ENABLE_RUST=1 python -c "from rasterstats import zonal_stats; print(zonal_stats('tests/upstream/data/polygons.shp','tests/upstream/data/slope.tif')[0])"
```

## Build and Test Commands

```bash
# Parity + API compatibility
PYTHONPATH=python pytest tests/upstream tests/compat -q

# Rust unit tests
cargo test --all

# Regression denylist
PYTHONPATH=python pytest tests/regression -q

# Forced Python fallback sweep
PYTHONPATH=python OXRS_DISABLE_RUST=1 pytest tests/upstream tests/compat -q

# Performance suites
PYTHONPATH=python pytest tests/perf -q -m perf_small --benchmark-only --benchmark-min-rounds=5
PYTHONPATH=python pytest tests/perf -q -m perf_large --benchmark-only --benchmark-min-rounds=5
```

## Benchmark Snapshot (2026-02-16)

See `benchmarks/results/2026-02-16.md`.

- Small fixture (`vacant-better`):
  - Zonal: Rust `290.9ms`, baseline `2264.8ms` (`7.78x`)
  - Point query: Rust `144.2ms`, baseline `1829.9ms` (`12.69x`)
- Large fixture (`copacetic-note` local):
  - Zonal: Rust `2.655s`, baseline `27.969s` (`10.53x`)
  - Point query: Rust `1.242s`, baseline `21.613s` (`17.41x`)

## Upstream Attribution

`oxidized-rasterstats` is built from and compatible with the upstream
[`python-rasterstats`](https://github.com/perrygeo/python-rasterstats) project by
Matthew Perry and contributors.

- Upstream project: `python-rasterstats` (author: Matthew Perry / `perrygeo`)
- Pinned upstream snapshot: `vendor/upstream_rasterstats/SHA.txt`
- Vendored upstream source/tests: `vendor/upstream_rasterstats/`
- Imported parity fixtures/tests: `tests/upstream/`
- Python compatibility copies based on upstream modules: `python/rasterstats/_upstream_main.py`, `python/rasterstats/_upstream_point.py`, `python/rasterstats/io.py`, `python/rasterstats/utils.py`, `python/rasterstats/cli.py`

See `docs/attribution.md` for attribution and licensing details.

## License

- Project license: BSD 3-Clause (`LICENSE`)
- Copyright and component-level ownership notes: `NOTICE.md`
- Upstream `python-rasterstats` license snapshot: `vendor/upstream_rasterstats/LICENSE.txt`

## Repository Layout

- `python/rasterstats/`: compatibility package + dispatcher + upstream fallback copies
- `src/`: Rust core (`zonal`, `point`, `raster`, `stats`, `errors`, `geom`)
- `tests/upstream/`: imported upstream tests
- `tests/regression/`: issue denylist coverage
- `tests/perf/`: benchmark harness
- `scripts/`: upstream sync, fixture generation, API manifest tooling
- `docs/upstream_issues/`: issue snapshots
- `vendor/upstream_rasterstats/`: pinned upstream source/tests

## Review Guide

Start with `docs/review_guide.md` for scope, command log, and file-level review map.
