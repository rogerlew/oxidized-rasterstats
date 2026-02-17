# Review Guide

This document summarizes what changed and how to review the codebase efficiently.

## Scope of This Revision

1. Added Rust zonal optimization based on GDAL rasterized masks + bulk window reads.
2. Preserved Python fallback compatibility with default-on Rust dispatch and `OXRS_DISABLE_RUST=1` override.
3. Added/maintained parity, regression, and benchmark harness coverage.
4. Updated packaging/CI paths for `maturin` workflows.
5. Disabled ExecPlan-as-mandatory policy in `AGENTS.md`.

## Key Implementation Areas

- Rust zonal core:
  - `src/zonal.rs`
  - `src/raster.rs`
- Rust/Python bridge:
  - `src/lib.rs`
  - `python/rasterstats/_dispatch.py`
  - `python/rasterstats/main.py`
- Benchmark harness:
  - `tests/perf/test_perf_weppcloud.py`
  - `benchmarks/results/2026-02-16.md`
- Regression and parity coverage:
  - `tests/upstream/*`
  - `tests/regression/*`
  - `tests/compat/*`

## Behavior and Compatibility Notes

1. Import/API compatibility for `rasterstats` is preserved.
2. Rust zonal and point-query dispatch are default-on for eligible calls.
3. Invalid file-like strings are routed to Python fallback (avoids Rust path open errors for WKT/invalid inputs).
4. In-memory feature collections are normalized through temporary GeoJSON when Rust dispatch is enabled to preserve cross-input consistency.
5. Non-overlapping-zone `nodata` footprint counts now match upstream behavior; no post-processing normalization to `0` is applied.
6. Upstream attribution for Matthew Perry and `python-rasterstats` is documented in `docs/attribution.md`.
7. Project-level copyright and artifact ownership notes are documented in `NOTICE.md`.

## Reproduction Commands

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install maturin pytest pytest-cov pytest-benchmark patchelf

python scripts/sync_upstream.py --repo /workdir/python-rasterstats --sha e51b48a62e3ac7e4ef4a81a8c2a8e5b90fa5e8ac
python scripts/build_weppcloud_fixtures.py --small-run /wc1/runs/va/vacant-better --large-run /wc1/runs/co/copacetic-note --out tests/fixtures/weppcloud --profile all

maturin develop --release

PYTHONPATH=python pytest tests/upstream tests/compat -q
PYTHONPATH=python pytest tests/regression -q
PYTHONPATH=python OXRS_DISABLE_RUST=1 pytest tests/upstream tests/compat -q

PYTHONPATH=python pytest tests/perf -q -m perf_small --benchmark-only --benchmark-json benchmarks/results/2026-02-16-small.json
PYTHONPATH=python pytest tests/perf -q -m perf_large --benchmark-only --benchmark-json benchmarks/results/2026-02-16-large.json
```

## Latest Verified Results

- Parity + compat (default dispatch): `114 passed, 2 skipped`
- Regression (default dispatch): `11 passed`
- Parity + compat (forced Python fallback): `114 passed, 2 skipped`
- Benchmarks: all perf tests pass; zonal and point-query targets exceeded on both fixture tiers.

## Reviewer Checklist

1. Confirm Rust zonal mask logic in `src/zonal.rs` aligns with expected rasterization semantics.
2. Validate fallback guards and exception behavior in `python/rasterstats/_dispatch.py`.
3. Verify no API/signature drift in `tests/compat/test_api_surface.py`.
4. Verify denylist issue coverage in `tests/regression/test_issue_*.py`.
5. Verify benchmark claims against `benchmarks/results/2026-02-16.md` and JSON artifacts.
