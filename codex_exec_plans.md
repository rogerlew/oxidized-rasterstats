# Build `oxidized-rasterstats` as a Drop-in, Rust-Accelerated `python-rasterstats` Replacement

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

## Purpose / Big Picture

After this work, users can install `oxidized-rasterstats` and keep using the same import paths and function calls they already use for `python-rasterstats` (`from rasterstats import zonal_stats, point_query`). The public API and CLI behavior remain compatible, while the heavy computation runs in Rust with GDAL-backed I/O and rasterization for better throughput and lower memory pressure.

Observable success is:

1. The upstream `python-rasterstats` tests pass against this repo's `rasterstats` package.
2. New regression tests for known upstream open bug reports pass.
3. Benchmarks show the Rust fast path is materially faster than upstream Python on representative polygon and point workloads.

## Scope and Non-Goals

In scope:

1. API-compatibility for the `rasterstats` module surface shipped by upstream `0.20.0` (and current `main` snapshot at commit `e51b48a62e3ac7e4ef4a81a8c2a8e5b90fa5e8ac`, dated 2025-11-17).
2. Rust acceleration through PyO3 bindings.
3. GDAL usage in Rust for raster access and geometry rasterization.
4. `maturin` for build + wheel packaging.
5. Reuse of upstream tests plus additional Rust/Python tests.

Out of scope for initial delivery:

1. New user-facing features not present upstream (unless required to fix known bugs).
2. Reprojection/regridding workflows (upstream design goal is to avoid those).
3. Full multi-band feature expansion beyond current upstream semantics.

## Hard Constraints

1. Top-level Python package name must be `rasterstats` for drop-in import compatibility.
2. Public function signatures and return types must match upstream unless a documented bug fix requires safer behavior.
3. Rust code must use GDAL (not only pure Rust raster readers).
4. Build system must be `maturin`.
5. Fast path must never silently return numerically different results without test coverage and explicit decision log entry.

## Progress

- [x] (2026-02-16 22:17Z) Collected upstream API/test context from local checkout at `/workdir/python-rasterstats`.
- [x] (2026-02-16 22:17Z) Pulled current open issues via GitHub API (`state=open`, `per_page=100`) and captured issue-driven risk list.
- [x] (2026-02-16 22:17Z) Replaced generic plan template with this repo-specific autonomous ExecPlan.
- [x] (2026-02-16 22:21Z) Incorporated WEPPcloud fixture sources and dataset-tier benchmark strategy (`/wc1/runs/co/copacetic-note` large, `/wc1/runs/va/vacant-better` small).
- [x] (2026-02-16 22:53Z) Initialized project skeleton (`pyproject.toml`, `Cargo.toml`, PyO3 module, Python package layout, Rust module layout).
- [x] (2026-02-16 22:53Z) Imported upstream compatibility layer and parity harness (`scripts/sync_upstream.py`, `tests/upstream`, `tests/compat`, API manifest tooling).
- [x] (2026-02-16 22:53Z) Implemented Rust GDAL-backed zonal fast path (`src/zonal.rs`) with Python dispatcher integration and fallback safety.
- [x] (2026-02-16 22:53Z) Implemented Rust GDAL-backed point-query fast path (`src/point.rs`) with interpolation handling and dispatcher integration.
- [x] (2026-02-16 22:53Z) Added denylist regression suite (`tests/regression/test_issue_*.py`) and passed full regression run.
- [x] (2026-02-16 23:08Z) Optimized Rust zonal path with GDAL rasterization masks + bulk window reads; benchmark harness now meets small/large zonal and point-query targets.
- [x] (2026-02-16 22:53Z) Added CI workflow with parity, regression, Rust tests, perf-smoke, and wheel build (`.github/workflows/ci.yml`).
- [x] (2026-02-16 22:53Z) Finalized packaging flow with `maturin` build artifacts and wheel-install smoke checks.
- [x] (2026-02-16 23:51Z) Converted staged TIFF fixtures to Git LFS pointers and added `.gitattributes` tracking for `*.tif`.
- [x] (2026-02-16 23:51Z) Audited staged fixture artifact sizes for GitHub limits; no staged blob exceeds 90 MB.
- [x] (2026-02-17 01:52Z) Removed non-overlap `nodata` normalization shim to restore strict upstream parity for boundless non-overlapping zones; updated regression/docs and revalidated parity suites.
- [x] (2026-02-17 02:23Z) Hardened dispatch observability (warning logs on Rust-path exceptions), upgraded PyO3 APIs/version to remove deprecations, removed dead Rust helpers, and upgraded perf/geopandas validation coverage.

## Surprises & Discoveries

- Observation: `/workdir/oxidized-rasterstats` currently has no implementation code (only `README.md` and this plan), so this is a full greenfield build.
  Evidence: `rg --files /workdir/oxidized-rasterstats` returned only `README.md`, `LICENSE`, and `codex_exec_plans.md`.

- Observation: Upstream has 27 open issues (excluding pull requests) as of 2026-02-16, including unresolved behavior bugs that affect interface reliability.
  Evidence: GitHub API query `https://api.github.com/repos/perrygeo/python-rasterstats/issues?state=open&per_page=100` filtered for non-PR issues.

- Observation: Upstream merged a fix for `progress=True` in 2025, but issue #303 remains open because the replacement logic still assumes `len(vectors)` exists.
  Evidence: upstream `src/rasterstats/main.py` uses `total = len(args[0])`.

- Observation: The user-provided WEPPcloud runs are suitable for fixture tiering and differ by roughly an order of magnitude in feature count.
  Evidence: `/wc1/runs/co/copacetic-note/dem/wbt/subcatchments.geojson` has 9,429 features and `channels.geojson` has 12,477 features; `/wc1/runs/va/vacant-better/dem/wbt/subcatchments.geojson` has 802 and `channels.geojson` has 1,205.

- Observation: Both runs expose centroid lon/lat directly in hillslope parquet data, which can generate high-volume point-query fixtures without extra geometry joins.
  Evidence: `watershed/hillslopes.parquet` columns include `centroid_lon` and `centroid_lat` in both runs.

- Observation: `maturin build` required `patchelf` in this environment because the wheel bundles many GDAL-linked shared libraries.
  Evidence: Initial `maturin build --release` failed with `Failed to execute 'patchelf'`; installing `patchelf` resolved the build.

- Observation: `fiona` layer probing on WEPPcloud GeoJSON paths was unreliable in baseline perf calls, while the same payload worked as loaded FeatureCollections.
  Evidence: `fallback_zonal_stats(path_to_geojson, ...)` failed in perf tests; loading JSON and passing mapping succeeded.

- Observation: `pyarrow` was not installed in the command-script bootstrap environment, so fixture point generation used deterministic centroid fallback from `subcatchments.geojson`.
  Evidence: `scripts/build_weppcloud_fixtures.py` produced `point_source: subcatchments.geojson(centroid-fallback)` for both tiers.

- Observation: Replacing per-pixel geometry predicates with GDAL rasterized masks reduced zonal runtime by an order of magnitude on both fixture tiers.
  Evidence: zonal benchmark moved from ~`4.7s` to `290.9ms` on `small` and from ~`21.9s` to `2.65s` on `large_local`.

- Observation: Current committed fixture corpus is comfortably below GitHub's 100 MB hard file limit after converting TIFF assets to LFS pointers.
  Evidence: staged non-LFS largest file is `tests/fixtures/weppcloud/small/dem/wbt/subcatchments.WGS.geojson` at `1,026,349` bytes; staged `*.tif` entries resolve to LFS pointers.

## Decision Log

- Decision: Define "drop-in replacement" as import-path compatibility (`import rasterstats`) plus callable signature compatibility and CLI option compatibility.
  Rationale: Distribution names can differ (`oxidized-rasterstats`) while preserving user code compatibility.
  Date/Author: 2026-02-16 / Codex.

- Decision: Keep a Python compatibility shim and route only hot paths into Rust; fallback to Python for hard-to-accelerate dynamic behaviors (`add_stats`, `zone_func`, `raster_out` edge cases).
  Rationale: Guarantees correctness and API fidelity while still delivering large speedups on common workloads.
  Date/Author: 2026-02-16 / Codex.

- Decision: Pin compatibility target to upstream commit `e51b48a` and keep an explicit sync script for future rebases.
  Rationale: Reproducible parity and deterministic tests.
  Date/Author: 2026-02-16 / Codex.

- Decision: Treat unresolved upstream bug reports as a denylist: implement regression tests so the new implementation does not reproduce those bugs.
  Rationale: User explicitly requested issue-aware behavior and non-duplication of known interface bugs.
  Date/Author: 2026-02-16 / Codex.

- Decision: Use a two-tier WEPPcloud fixture strategy: commit a small stable fixture derived from `/wc1/runs/va/vacant-better`, and generate a large local-only fixture from `/wc1/runs/co/copacetic-note` for heavy benchmarks.
  Rationale: Keeps CI lightweight while preserving realistic large-scale performance testing.
  Date/Author: 2026-02-16 / Codex.

- Decision: Gate Rust dispatch behind `OXRS_ENABLE_RUST=1` (with fallback default-on) until broader numeric parity is guaranteed across all geometry types.
  Rationale: Preserves strict upstream compatibility for default behavior while still exposing Rust fast paths for targeted benchmarks and controlled runs.
  Date/Author: 2026-02-16 / Codex.

- Decision: Apply compatibility-layer post-processing for nodata non-overlap behavior (#105/#243) when fallback output shows `count == 0` outside raster bounds.
  Rationale: Prevents known upstream nodata overcount behavior without changing upstream test expectations for overlapping all-nodata zones.
  Date/Author: 2026-02-16 / Codex.

- Decision: Revert non-overlap `nodata` post-processing and preserve upstream semantics for strict parity.
  Rationale: Acceptance review follow-up requested parity with upstream Python behavior for non-overlapping zones; Rust core already matched upstream and the remaining drift came from Python normalization.
  Date/Author: 2026-02-17 / Codex.

- Decision: Log warning-level events for exception-triggered Rust dispatch fallback instead of silently returning `None`.
  Rationale: Preserve fallback safety while making fast-path failures observable in production operations.
  Date/Author: 2026-02-17 / Codex.

- Decision: Use centroid fallback from `subcatchments.geojson` when parquet reader dependencies are absent.
  Rationale: Keeps fixture generation idempotent and runnable under the command-script bootstrap environment.
  Date/Author: 2026-02-16 / Codex.

- Decision: Record temporary performance waiver for zonal targets in Milestone 5 while accepting the point-query speedup results.
  Rationale: Benchmark data shows zonal speedup `0.52x` on small and `1.27x` on large vs required `>=2.0x` / `>=2.5x`; this needs follow-up optimization work.
  Date/Author: 2026-02-16 / Codex.

- Decision: Re-implement zonal feature masking using GDAL rasterization into in-memory `MEM` rasters instead of cell-by-cell geometric predicates.
  Rationale: This changes complexity from many geometry predicate calls per cell to one GDAL rasterization call per feature and enables contiguous window reads, which dramatically improves throughput.
  Date/Author: 2026-02-16 / Codex.

- Decision: Close the temporary zonal-performance waiver after optimization rerun.
  Rationale: Updated benchmarks show zonal speedups `7.78x` (small) and `10.53x` (large), exceeding release gates.
  Date/Author: 2026-02-16 / Codex.

- Decision: Track all repository `*.tif` test fixtures with Git LFS and gate staged artifacts with a size audit before commit.
  Rationale: Prevent GitHub file-size limit violations while keeping fixture provenance in-repo.
  Date/Author: 2026-02-16 / Codex.

## Outcomes & Retrospective

Execution outcome (2026-02-16):

1. Milestones 0, 1, 1A, 2, 3, 4, and 6 were implemented with working artifacts, and their acceptance checks were executed locally.
2. Command-script validation runs pass: parity/compat (`114 passed, 2 skipped`), Rust tests (`2 passed`), regression (`11 passed`), perf small/large (all benchmark tests passed).
3. Open-issue denylist coverage now exists as explicit `tests/regression/test_issue_*.py` files for #303, #294, #288, #246, #243, #227, #215, #285, #286, #105, and #98.
4. Packaging flow is operational with `maturin develop` and `maturin build`; wheel install smoke tests pass in a fresh virtual environment.
5. Performance targets are met on both fixture tiers for zonal and point-query workloads after zonal mask-path optimization.
6. Fixture storage now uses Git LFS for TIFF assets (`21` tracked TIFF files), and staged artifacts pass file-size checks for GitHub limits.
7. Non-overlap `nodata` footprint behavior now matches upstream Python semantics for both Rust-dispatch and fallback code paths.
8. Dispatch fallback health is now observable through warning logs, Rust compile warnings from PyO3/dead-code are cleared, and benchmark/geopandas test posture is hardened (multi-round perf, no geopandas skips in validated environment).

Concrete-step status:

1. `python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install maturin pytest pytest-cov pytest-benchmark` -> PASS.
2. `python scripts/sync_upstream.py --repo /workdir/python-rasterstats --sha e51b48a62e3ac7e4ef4a81a8c2a8e5b90fa5e8ac` -> PASS (idempotent re-run verified).
3. `python scripts/build_weppcloud_fixtures.py --small-run /wc1/runs/va/vacant-better --large-run /wc1/runs/co/copacetic-note --out tests/fixtures/weppcloud --profile all` -> PASS.
4. `maturin develop --release` -> PASS (after one compile-fix iteration for GDAL index types).
5. `PYTHONPATH=python pytest tests/upstream tests/compat -q` -> PASS (`114 passed, 2 skipped`).
6. `cargo test --all` -> PASS (`2 passed`).
7. `PYTHONPATH=python pytest tests/regression -q` -> PASS (`11 passed`).
8. `PYTHONPATH=python pytest tests/perf -q -m perf_small --benchmark-only` -> PASS.
9. `PYTHONPATH=python pytest tests/perf -q -m perf_large --benchmark-only` -> PASS.
10. `PYTHONPATH=python pytest tests/perf -q -m perf_small --benchmark-only --benchmark-json benchmarks/results/2026-02-16-small.json` -> PASS (`small zonal speedup 7.78x`).
11. `PYTHONPATH=python pytest tests/perf -q -m perf_large --benchmark-only --benchmark-json benchmarks/results/2026-02-16-large.json` -> PASS (`large zonal speedup 10.53x`).

## Context and Orientation

Upstream compatibility baseline is `python-rasterstats` in `/workdir/python-rasterstats`.

Primary upstream API files:

1. `src/rasterstats/__init__.py`
2. `src/rasterstats/main.py`
3. `src/rasterstats/point.py`
4. `src/rasterstats/io.py`
5. `src/rasterstats/utils.py`
6. `src/rasterstats/cli.py`

Primary upstream tests to reuse:

1. `tests/test_zonal.py`
2. `tests/test_point.py`
3. `tests/test_io.py`
4. `tests/test_utils.py`
5. `tests/test_cli.py`

Reference patterns to borrow from `/workdir/wepppyo3`:

1. `raster_characteristics/Cargo.toml` for PyO3 crate conventions (`cdylib`, explicit `pyo3` features).
2. `wepp_viz/src/lib.rs` for Rust error-to-Python exception mapping style.
3. `README.md` build notes for platform quirks (especially macOS linker behavior for extension modules).

Important adaptation: `wepppyo3` uses direct Cargo workflows, but this project must use `maturin` as the packaging/build interface.

Key terms used in this plan:

1. "Fast path" means code paths dispatched to Rust for performance-sensitive default behavior.
2. "Fallback path" means Python implementation used for compatibility in dynamic/custom call scenarios.
3. "Boundless read" means allowing windows outside raster extent and filling with nodata-like values.
4. "Parity" means output keys, scalar values, warnings/exceptions, and ordering behavior are compatible with upstream tests.

Canonical WEPPcloud fixture sources:

1. Large benchmark source: `/wc1/runs/co/copacetic-note`
2. Small/CI fixture source: `/wc1/runs/va/vacant-better`
3. Vector layers in both UTM and WGS84: `dem/wbt/subcatchments.geojson`, `dem/wbt/subcatchments.WGS.geojson`, `dem/wbt/channels.geojson`, `dem/wbt/channels.WGS.geojson`
4. Continuous rasters: `dem/wbt/relief.tif`, `dem/wbt/fvslop.tif`, `dem/wbt/discha.tif`, `dem/wbt/floaccum.tif`, `dem/wbt/taspec.tif`
5. Categorical raster: `landuse/nlcd.tif`
6. Point-query source: `watershed/hillslopes.parquet` columns `centroid_lon` and `centroid_lat`

Observed scale snapshot (2026-02-16):

1. `copacetic-note`: 9,429 subcatchments, 12,477 channels, 5,422 hillslopes.
2. `vacant-better`: 802 subcatchments, 1,205 channels, 399 hillslopes.

## Upstream Interface Contract (Must Match)

The `rasterstats` top-level exports must include:

1. `__version__`
2. `cli`
3. `gen_point_query`
4. `gen_zonal_stats`
5. `point_query`
6. `raster_stats`
7. `zonal_stats`

Key callable signatures to preserve:

1. `zonal_stats(*args, **kwargs)`
2. `raster_stats(*args, **kwargs)`
3. `gen_zonal_stats(vectors, raster, layer=0, band=1, nodata=None, affine=None, stats=None, all_touched=False, categorical=False, category_map=None, add_stats=None, zone_func=None, raster_out=False, prefix=None, geojson_out=False, boundless=True, **kwargs)`
4. `point_query(*args, **kwargs)`
5. `gen_point_query(vectors, raster, band=1, layer=0, nodata=None, affine=None, interpolate="bilinear", property_name="value", geojson_out=False, boundless=True)`

CLI contracts to preserve (same options and defaults):

1. `rio zonalstats ...`
2. `rio pointquery ...`

Behavior contracts to preserve:

1. `zonal_stats(...)` and `point_query(...)` return lists.
2. `gen_*` variants return generators.
3. `geojson_out=True` preserves input feature geometry/properties and appends computed properties.
4. Deprecated aliases still warn (`raster_stats`, `band_num`, `transform`, `copy_properties`).
5. Categorical and percentile stats behave like upstream tests assert.

## Open-Issue Snapshot and Bug Denylist

Snapshot date: 2026-02-16.

Source command:

    curl -sS 'https://api.github.com/repos/perrygeo/python-rasterstats/issues?state=open&per_page=100'

Persist snapshot into repo as:

1. `docs/upstream_issues/open_issues_2026-02-16.json`
2. `docs/upstream_issues/open_issues_2026-02-16.md` (human summary)

High-priority bug reports to prevent in this implementation:

1. #303 progress handling for non-sized iterables.
2. #294 point-query corner behavior near nodata boundaries.
3. #288 unclear error for incomplete shapefile sidecars.
4. #246 masked NumPy array handling.
5. #243 nodata stat on empty rasterization.
6. #227 boundless read performance collapse.
7. #215 infinity values leaking into results.
8. #285 memory growth across loops.
9. #286 segmentation faults on large inputs.
10. #105 nodata count including non-overlap cells.
11. #98 non-standard affine transform handling.

Feature-request issues to track but not block initial release:

1. #295 CRS metadata in output.
2. #271 `properties_out` option.
3. #208 remote file context handling.
4. #73 broader multiband capabilities.

Each denylist bug must get one dedicated regression test file named `tests/regression/test_issue_<number>_<slug>.py` (or Rust integration equivalent if lower-level).

## Target Repository Layout

Create this structure (paths are repo-relative):

1. `pyproject.toml` using `maturin` as build backend.
2. `Cargo.toml` (workspace root) and `src/lib.rs` for PyO3 extension entrypoint.
3. `python/rasterstats/` with compatibility package:
   - `__init__.py`
   - `_version.py`
   - `main.py`
   - `point.py`
   - `io.py`
   - `utils.py`
   - `cli.py`
   - `_dispatch.py` (fast-path routing policy)
   - `_fallback_py.py` (pure Python compatibility engine)
4. `rust_core/` modules under `src/` for implementation details:
   - `src/zonal.rs`
   - `src/point.rs`
   - `src/raster.rs`
   - `src/stats.rs`
   - `src/geom.rs`
   - `src/errors.rs`
5. `tests/upstream/` (copied/adapted upstream tests).
6. `tests/regression/` (issue-driven tests).
7. `tests/perf/` (benchmark scenarios and thresholds).
8. `scripts/sync_upstream.py` (copies pinned upstream files and fixtures).
9. `scripts/generate_api_manifest.py` and `tests/compat/test_api_surface.py`.
10. `docs/upstream_issues/` for issue snapshots.
11. `scripts/build_weppcloud_fixtures.py` (derives reproducible test/benchmark fixtures from WEPPcloud runs).
12. `tests/fixtures/weppcloud/small/` (committed CI fixture derived from `vacant-better`).
13. `tests/fixtures/weppcloud/large_local/` (gitignored, generated from `copacetic-note`).
14. `tests/fixtures/weppcloud/manifests/` (feature counts, CRS, nodata, source provenance).

## Architecture Plan

### Python Layer (Compatibility First)

1. Keep API signatures and docstrings near-upstream.
2. Keep flexible input parsing (`read_features`) in Python where dynamic object handling is naturally easier.
3. Add dispatch logic:
   - Rust fast path when arguments match supported acceleration profile.
   - Python fallback path otherwise.
4. Preserve warnings and exception types expected by upstream tests.

### Rust Layer (Performance Core)

1. Expose PyO3 functions in a private extension module (for example `rasterstats._rs`).
2. Use GDAL in Rust for:
   - raster dataset open/read,
   - geometry decode (WKB/WKT),
   - geometry rasterization into masks,
   - windowed reads and transform-aware indexing.
3. Implement streaming feature processing to avoid whole-dataset buffering.
4. Ensure explicit nodata/nan semantics and deterministic accumulation dtypes.
5. Keep custom Python callback stats (`add_stats`, `zone_func`) in fallback mode unless safe callback bridging is proven with benchmarks.

### Build and Packaging

1. `maturin` drives wheel/sdist builds.
2. Wheel provides package `rasterstats` and extension module inside it.
3. Project distribution name is `oxidized-rasterstats`; import name remains `rasterstats`.
4. CLI entry points preserve `rasterio.rio_plugins` plugin names (`zonalstats`, `pointquery`).

## Milestones

## Milestone 0: Bootstrap and Pin Upstream Baseline

Create minimal buildable package and pin upstream compatibility source.

Work:

1. Initialize `pyproject.toml` (`maturin` backend, project metadata, optional deps for tests/docs/perf).
2. Initialize Rust crate with PyO3 module exporting one `healthcheck()` function.
3. Add `python/rasterstats/__init__.py` and `_version.py` with placeholder version.
4. Add `scripts/sync_upstream.py` to copy pinned upstream files/tests/fixtures into `vendor/upstream_rasterstats/` and `tests/upstream/`.
5. Commit the pinned upstream SHA in `vendor/upstream_rasterstats/SHA.txt`.

Acceptance:

1. `maturin develop` succeeds.
2. `python -c "import rasterstats; print(rasterstats.__version__)"` succeeds.
3. `python scripts/sync_upstream.py --sha e51b48a62e3ac7e4ef4a81a8c2a8e5b90fa5e8ac` is idempotent.

## Milestone 1: Compatibility Harness Before Optimization

Establish parity gates before implementing acceleration.

Work:

1. Copy upstream Python modules into `python/rasterstats/` as initial fallback implementation.
2. Add `tests/compat/test_api_surface.py` to verify exports/signatures/warnings.
3. Import upstream tests into `tests/upstream/` and update imports only where pathing differs.
4. Add lightweight runner script `scripts/run_parity_tests.sh`.
5. Add fixture builder `scripts/build_weppcloud_fixtures.py` with reproducible outputs:
   - UTM/WGS subcatchments and channels.
   - Centroid point set from `watershed/hillslopes.parquet` (`centroid_lon`, `centroid_lat`).
   - Continuous and categorical rasters used by tests.
6. Commit only the `small` fixture outputs (from `vacant-better`) and manifest metadata.

Acceptance:

1. Baseline upstream tests pass against fallback implementation.
2. API surface test passes and fails if signature drift occurs.
3. `python scripts/build_weppcloud_fixtures.py --small-run /wc1/runs/va/vacant-better --out tests/fixtures/weppcloud --profile ci-small` succeeds idempotently.

## Milestone 1A: Fixture Pipeline and Data Provenance

Establish deterministic, source-aware fixture generation for large and small watershed scenarios.

Work:

1. Implement source validation in `scripts/build_weppcloud_fixtures.py` (required file checks for vectors, rasters, and hillslopes parquet).
2. Generate small committed fixture from `/wc1/runs/va/vacant-better` under `tests/fixtures/weppcloud/small/`.
3. Generate large local fixture from `/wc1/runs/co/copacetic-note` under `tests/fixtures/weppcloud/large_local/` (gitignored).
4. Emit provenance manifests under `tests/fixtures/weppcloud/manifests/` that include source paths, counts, CRS, nodata, and generation timestamp.
5. Add tests that verify fixture manifests and expected schema to catch accidental drift.

Acceptance:

1. Fixture generation is idempotent and re-runnable.
2. CI does not require direct access to `/wc1/runs/*`; it uses committed `small` fixture only.
3. Local benchmark mode uses `large_local` fixture when source path exists.

## Milestone 2: Rust Zonal Stats Fast Path

Implement accelerated zonal stats for default workflows.

Work:

1. Implement Rust function (name example):
   - `zonal_stats_wkb(features_wkb, raster_source, options) -> list[dict]`
2. Support stats set: default stats, optional stats, categorical, percentile, nodata, nan.
3. Implement `all_touched` and `boundless` semantics.
4. Preserve numeric behavior for `count`, `sum`, `mean`, `std`, `median`, `majority`, `minority`, `unique`, `range`.
5. Add Python dispatcher to route eligible `zonal_stats` calls to Rust.

Initial fast-path eligibility rule:

1. `add_stats is None`
2. `zone_func is None`
3. `raster_out is False`
4. Input vectors are parseable by current `read_features`.

Acceptance:

1. Upstream zonal tests pass.
2. Rust unit tests for stats kernels pass.
3. Regression tests for #105, #243, #246, #98 pass.

## Milestone 3: Rust Point Query Fast Path

Implement accelerated point query with robust interpolation edge handling.

Work:

1. Implement Rust point-query nearest and bilinear interpolation.
2. Preserve geometry flattening semantics (`geom_xys`) and 3D-to-2D handling.
3. Match return-shape behavior (single-value flattening).
4. Route eligible `point_query` calls through Rust.

Acceptance:

1. Upstream `test_point.py` passes.
2. Regression test for #294 passes.

## Milestone 4: Open-Issue Regression Suite and Error Semantics

Add explicit tests for open bug reports and clarify behavior where upstream is ambiguous.

Work:

1. Add regression files for all denylist issues.
2. For issues that require external data not available in CI, add minimized synthetic reproductions.
3. Normalize error messages for incomplete shapefile components (#288) and non-sized iterables with progress (#303).
4. Add memory/segfault protection tests where feasible (#285, #286) using stress tests and leak guards.

Acceptance:

1. `pytest tests/regression -q` passes.
2. No denylist bug is reproducible via included fixtures.

## Milestone 5: Performance and Memory Targets

Prove measurable acceleration and memory stability.

Work:

1. Add benchmarks under `tests/perf/` and/or `benchmarks/`:
   - polygon zonal stats on `vacant-better` small fixture and `copacetic-note` large fixture,
   - point queries from hillslope centroid points (`centroid_lon`, `centroid_lat`),
   - boundless-heavy workload using channels/subcatchments near raster edges.
2. Add comparison harness against upstream baseline loaded from `vendor/upstream_rasterstats`.
3. Tune hotspots (buffer reuse, dataset handle strategy, optional thread parallelism with safe GDAL handle ownership).

Performance budgets (initial release gate):

1. `zonal_stats` default stats: median wall-clock >= 2.0x faster than upstream on `vacant-better` full subcatchments fixture.
2. `zonal_stats` default stats: median wall-clock >= 2.5x faster than upstream on `copacetic-note` large subcatchments fixture.
3. `point_query` bilinear: median wall-clock >= 2.0x faster on centroid points from `vacant-better` and >= 2.5x on centroid points from `copacetic-note`.
4. Memory growth under repeated loop test (#285 scenario) remains bounded (no monotonic leak trend across 1,000 iterations).

Acceptance:

1. Benchmark report committed in `benchmarks/results/<date>.md`.
2. CI perf-smoke step confirms no catastrophic regressions.
3. Benchmark report includes separate sections for `small` and `large_local` WEPPcloud fixtures.

## Milestone 6: Packaging and Release Readiness

Ship installable artifacts that preserve drop-in behavior.

Work:

1. Finalize metadata for distribution `oxidized-rasterstats` with import package `rasterstats`.
2. Ensure plugin entry points for `rio zonalstats` / `rio pointquery` exist.
3. Add wheel build workflow via `maturin build`.
4. Add installation smoke test in CI:
   - create fresh venv,
   - install built wheel,
   - run API + CLI smoke commands.

Acceptance:

1. Built wheel installs and imports cleanly.
2. CLI plugin commands execute.
3. Full test suite and regression suite pass on CI matrix.

## Concrete Steps (Command Script)

Run from repository root `/workdir/oxidized-rasterstats` unless noted.

1. Bootstrap environment.

       python -m venv .venv
       . .venv/bin/activate
       pip install -U pip
       pip install maturin pytest pytest-cov pytest-benchmark

2. Sync upstream baseline.

       python scripts/sync_upstream.py --repo /workdir/python-rasterstats --sha e51b48a62e3ac7e4ef4a81a8c2a8e5b90fa5e8ac

3. Build WEPPcloud fixtures.

       python scripts/build_weppcloud_fixtures.py \
         --small-run /wc1/runs/va/vacant-better \
         --large-run /wc1/runs/co/copacetic-note \
         --out tests/fixtures/weppcloud \
         --profile all

4. Build extension in dev mode.

       maturin develop --release

5. Run parity tests.

       PYTHONPATH=python pytest tests/upstream tests/compat -q

6. Run Rust tests.

       cargo test --all

7. Run regression tests.

       PYTHONPATH=python pytest tests/regression -q

8. Run small-fixture performance comparison (CI-safe).

       PYTHONPATH=python pytest tests/perf -q -m perf_small --benchmark-only

9. Run large-fixture performance comparison (local).

       PYTHONPATH=python pytest tests/perf -q -m perf_large --benchmark-only

If `/wc1/runs/co/copacetic-note` is unavailable, large fixture benchmarks are skipped and reported as `SKIPPED (source unavailable)` rather than failure.

Expected success pattern:

1. No test collection errors.
2. No signature parity failures.
3. Benchmarks produce JSON/markdown artifacts and meet thresholds.

## Validation and Acceptance

Functional acceptance requires all of the following:

1. Public API parity tests pass.
2. Upstream test reuse suite passes.
3. Open-issue regression tests pass.
4. Rust unit/integration tests pass.
5. Benchmark thresholds are met or decision log documents an approved temporary waiver.

User-visible acceptance smoke checks:

1. Python import and call:

       python - <<'PY'
       from rasterstats import zonal_stats, point_query
       print(callable(zonal_stats), callable(point_query))
       PY

2. CLI plugin commands:

       rio zonalstats --help
       rio pointquery --help

3. Typical zonal stats run on fixture:

       python - <<'PY'
       from rasterstats import zonal_stats
       print(zonal_stats('/workdir/python-rasterstats/tests/data/polygons.shp', '/workdir/python-rasterstats/tests/data/slope.tif')[0])
       PY

## Idempotence and Recovery

1. `scripts/sync_upstream.py` must be idempotent; re-running it should not duplicate files.
2. Keep pure-Python fallback available at all times so partial Rust milestones do not block functionality.
3. If a Rust change breaks parity, set dispatcher to fallback mode by default and keep tests green before continuing.
4. Avoid destructive git operations; recovery is by incremental commits and reverting specific commits if needed.
5. Fixture generation is retry-safe: regenerate `small` and `large_local` outputs from source runs without manual cleanup.

## Interfaces and Dependencies

Python dependencies (project-level):

1. `numpy`
2. `affine`
3. `click`
4. `cligj`
5. `simplejson`
6. `shapely`
7. `rasterio` and `fiona` for compatibility/fallback paths and fixture handling

Rust dependencies (core):

1. `pyo3` (PyO3 bindings)
2. `numpy` crate (NumPy array interop)
3. `gdal` crate (GDAL dataset and geometry APIs)
4. `gdal-sys` where needed for rasterization calls not exposed in high-level crate
5. `thiserror` and `anyhow` (error handling)
6. `rayon` (optional, after correctness lock)

Version policy:

1. Start with currently available stable versions at implementation time (`pyo3 0.28.x`, `gdal 0.19.x`, `maturin 1.12.x` observed on 2026-02-16).
2. Pin exact versions in lockfiles and document changes in decision log.

## Open-Issue Link List (Snapshot 2026-02-16)

1. https://github.com/perrygeo/python-rasterstats/issues/305
2. https://github.com/perrygeo/python-rasterstats/issues/303
3. https://github.com/perrygeo/python-rasterstats/issues/295
4. https://github.com/perrygeo/python-rasterstats/issues/294
5. https://github.com/perrygeo/python-rasterstats/issues/291
6. https://github.com/perrygeo/python-rasterstats/issues/288
7. https://github.com/perrygeo/python-rasterstats/issues/286
8. https://github.com/perrygeo/python-rasterstats/issues/285
9. https://github.com/perrygeo/python-rasterstats/issues/271
10. https://github.com/perrygeo/python-rasterstats/issues/246
11. https://github.com/perrygeo/python-rasterstats/issues/243
12. https://github.com/perrygeo/python-rasterstats/issues/227
13. https://github.com/perrygeo/python-rasterstats/issues/215
14. https://github.com/perrygeo/python-rasterstats/issues/214
15. https://github.com/perrygeo/python-rasterstats/issues/208
16. https://github.com/perrygeo/python-rasterstats/issues/206
17. https://github.com/perrygeo/python-rasterstats/issues/188
18. https://github.com/perrygeo/python-rasterstats/issues/165
19. https://github.com/perrygeo/python-rasterstats/issues/157
20. https://github.com/perrygeo/python-rasterstats/issues/133
21. https://github.com/perrygeo/python-rasterstats/issues/124
22. https://github.com/perrygeo/python-rasterstats/issues/108
23. https://github.com/perrygeo/python-rasterstats/issues/105
24. https://github.com/perrygeo/python-rasterstats/issues/98
25. https://github.com/perrygeo/python-rasterstats/issues/97
26. https://github.com/perrygeo/python-rasterstats/issues/90
27. https://github.com/perrygeo/python-rasterstats/issues/73

## Revision Note

2026-02-16: Replaced the generic planning-template text with a concrete autonomous implementation ExecPlan for `oxidized-rasterstats`, including upstream issue snapshot integration, API parity contract, Rust/GDAL/maturin architecture, milestone execution script, and measurable acceptance gates.
2026-02-16: Added WEPPcloud fixture strategy using `/wc1/runs/va/vacant-better` (small/CI) and `/wc1/runs/co/copacetic-note` (large/local), with explicit layer selection, centroid-point extraction from `hillslopes.parquet`, fixture generation workflow, and small/large benchmark gates.
2026-02-16: Executed milestones through packaging, added GDAL-backed Rust modules plus Python fallback dispatcher, imported upstream parity harness, added denylist regression suite and perf harness, built fixtures/manifests, generated upstream-issue snapshot docs, produced benchmark report, and documented temporary zonal-performance waiver.
2026-02-16: Optimized Rust zonal implementation by switching to GDAL in-memory rasterized masks with bulk window reads; refreshed perf artifacts and closed the temporary zonal-performance waiver after exceeding benchmark gates.
