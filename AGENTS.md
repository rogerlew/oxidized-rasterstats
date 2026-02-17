# AGENTS.md

## Scope

These instructions apply to the entire `oxidized-rasterstats` repository.

## Primary Goals

1. Preserve drop-in compatibility for import path `rasterstats`.
2. Keep GDAL-backed Rust fast paths for `zonal_stats` and `point_query`.
3. Preserve safe Python fallback behavior when Rust dispatch is ineligible or fails.
4. Keep build and packaging driven by `maturin`.

## Planning Policy

`codex_exec_plans.md` is retained as historical context and implementation log.

For normal work:

1. Follow direct user instructions first.
2. Use repository code/tests as source of truth.
3. Use `codex_exec_plans.md` only when explicitly requested.

## Repository Map

1. `python/rasterstats/`:
   - Public compatibility API and dispatch logic.
   - Rust/Python fallback orchestration.
2. `src/`:
   - Rust core (GDAL-backed zonal/point/stats/raster/error modules).
3. `tests/upstream/`:
   - Upstream parity suite.
4. `tests/compat/`:
   - API/dispatch compatibility checks.
5. `tests/regression/`:
   - Issue-driven denylist regression tests.
6. `tests/perf/`:
   - Benchmark harness.
7. `.github/workflows/ci.yml`:
   - PR/push validation workflow.
8. `.github/workflows/release-wheels.yml`:
   - Tag-driven wheel/sdist build and PyPI publish workflow.

## Local Prerequisites

1. Python `>=3.9`.
2. Rust stable toolchain.
3. GDAL runtime + dev headers (`gdal-bin`, `libgdal-dev` on Ubuntu).
4. `git-lfs` installed and initialized.

## Local Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e ".[test,perf]"
pip install maturin
git lfs install --local
git lfs pull
maturin develop --release
```

## Required Validation Commands

Run these for functional changes:

```bash
# default dispatch (Rust eligible calls enabled)
PYTHONPATH=python pytest tests/upstream tests/compat -q

# forced fallback path
PYTHONPATH=python OXRS_DISABLE_RUST=1 pytest tests/upstream tests/compat -q

# denylist regressions
PYTHONPATH=python pytest tests/regression -q

# Rust unit tests
cargo test --all
```

For performance-affecting changes:

```bash
PYTHONPATH=python pytest tests/perf -q -m perf_small --benchmark-only --benchmark-min-rounds=5
PYTHONPATH=python pytest tests/perf -q -m perf_large --benchmark-only --benchmark-min-rounds=5
```

## Dispatch and Observability Rules

1. Default mode is Rust-on when eligible.
2. `OXRS_DISABLE_RUST=1` forces fallback mode.
3. Exception-triggered Rust fallback is expected to emit warning logs from
   `rasterstats._dispatch`.
4. Do not silently change semantics between Rust and fallback paths without
   tests and documentation updates.

## CI Notes

`ci.yml` currently does the following on `push` and `pull_request`:

1. Checks out repo with LFS enabled (`lfs: true`).
2. Creates `.venv` and exports `VIRTUAL_ENV`/`PATH`.
3. Installs GDAL and `git-lfs`.
4. Runs `git lfs pull` before tests.
5. Runs parity/compat, Rust tests, regressions, perf smoke, and wheel build.

If CI reports raster format errors for `.tif`, verify LFS pull occurred.

## PyPI Release Workflow

`release-wheels.yml` is tag-driven (`v*`) and uses Trusted Publishing.

Current behavior:

1. Build Linux wheels for CPython `3.9`-`3.12`.
2. Build `sdist`.
3. Publish via `pypa/gh-action-pypi-publish` using `environment: pypi`.

Release runbook:

1. Bump versions in:
   - `pyproject.toml`
   - `Cargo.toml`
   - `python/rasterstats/_version.py` (compatibility version string)
2. Commit and push `main`.
3. Create and push tag `vX.Y.Z`.
4. Verify `Release Wheels` workflow completes and publishes expected artifacts.

## LFS Fixture Policy

1. Keep raster fixtures (`*.tif`) in Git LFS.
2. If adding new TIFF fixtures:
   - Ensure `.gitattributes` tracks `*.tif`.
   - Re-index files as LFS pointers if needed.
3. Do not commit large binary TIFFs as regular Git blobs.

## Documentation Expectations

When behavior changes, update relevant docs:

1. `README.md` for user-facing behavior changes.
2. `docs/review_guide.md` for reviewer/operator notes.
3. `docs/acceptance-test-review.md` when acceptance findings are resolved.
4. `codex_exec_plans.md` progress/decision/outcome sections when requested.
