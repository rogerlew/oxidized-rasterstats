from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

import pytest

from rasterstats import point_query, zonal_stats
from rasterstats._dispatch import _rust_available_default_on
from rasterstats._fallback_py import fallback_point_query, fallback_zonal_stats

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "weppcloud"
BENCHMARK_ROUNDS = max(5, int(os.environ.get("OXRS_BENCHMARK_ROUNDS", "5")))
BENCHMARK_ITERATIONS = max(1, int(os.environ.get("OXRS_BENCHMARK_ITERATIONS", "1")))


@contextmanager
def unset_var(name: str):
    old = os.environ.pop(name, None)
    try:
        yield
    finally:
        if old is not None:
            os.environ[name] = old


def _run_benchmark(benchmark, fn):
    return benchmark.pedantic(
        fn,
        rounds=BENCHMARK_ROUNDS,
        iterations=BENCHMARK_ITERATIONS,
    )


def _paths(tier: str) -> tuple[Path, Path, Path]:
    root = FIXTURE_ROOT / tier
    vectors = root / "dem/wbt/subcatchments.geojson"
    raster = root / "dem/wbt/relief.tif"
    points = root / "watershed/hillslope_points.geojson"
    return vectors, raster, points


def _skip_if_missing(tier: str) -> None:
    vectors, raster, points = _paths(tier)
    if not vectors.exists() or not raster.exists() or not points.exists():
        pytest.skip(f"fixture tier unavailable: {tier}")


def _load_feature_collection(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.perf_small
@pytest.mark.benchmark(group="small_zonal")
def test_perf_small_zonal_rust(benchmark):
    _skip_if_missing("small")
    vectors, raster, _ = _paths("small")

    def run():
        with unset_var("OXRS_DISABLE_RUST"):
            assert _rust_available_default_on()
            return zonal_stats(vectors, raster, stats="count mean")

    out = _run_benchmark(benchmark, run)
    assert out[0]["count"] >= 0


@pytest.mark.perf_small
@pytest.mark.benchmark(group="small_zonal")
def test_perf_small_zonal_upstream(benchmark):
    _skip_if_missing("small")
    vectors, raster, _ = _paths("small")
    feature_collection = _load_feature_collection(vectors)

    def run():
        return fallback_zonal_stats(feature_collection, raster, stats="count mean")

    out = _run_benchmark(benchmark, run)
    assert out[0]["count"] >= 0


@pytest.mark.perf_small
@pytest.mark.benchmark(group="small_point")
def test_perf_small_point_rust(benchmark):
    _skip_if_missing("small")
    _, raster, points = _paths("small")

    def run():
        with unset_var("OXRS_DISABLE_RUST"):
            assert _rust_available_default_on()
            return point_query(points, raster, interpolate="bilinear")

    out = _run_benchmark(benchmark, run)
    assert len(out) > 0


@pytest.mark.perf_small
@pytest.mark.benchmark(group="small_point")
def test_perf_small_point_upstream(benchmark):
    _skip_if_missing("small")
    _, raster, points = _paths("small")

    def run():
        return fallback_point_query(points, raster, interpolate="bilinear")

    out = _run_benchmark(benchmark, run)
    assert len(out) > 0


@pytest.mark.perf_large
@pytest.mark.benchmark(group="large_zonal")
def test_perf_large_zonal_rust(benchmark):
    _skip_if_missing("large_local")
    vectors, raster, _ = _paths("large_local")

    def run():
        with unset_var("OXRS_DISABLE_RUST"):
            assert _rust_available_default_on()
            return zonal_stats(vectors, raster, stats="count mean")

    out = _run_benchmark(benchmark, run)
    assert out[0]["count"] >= 0


@pytest.mark.perf_large
@pytest.mark.benchmark(group="large_zonal")
def test_perf_large_zonal_upstream(benchmark):
    _skip_if_missing("large_local")
    vectors, raster, _ = _paths("large_local")
    feature_collection = _load_feature_collection(vectors)

    def run():
        return fallback_zonal_stats(feature_collection, raster, stats="count mean")

    out = _run_benchmark(benchmark, run)
    assert out[0]["count"] >= 0


@pytest.mark.perf_large
@pytest.mark.benchmark(group="large_point")
def test_perf_large_point_rust(benchmark):
    _skip_if_missing("large_local")
    _, raster, points = _paths("large_local")

    def run():
        with unset_var("OXRS_DISABLE_RUST"):
            assert _rust_available_default_on()
            return point_query(points, raster, interpolate="bilinear")

    out = _run_benchmark(benchmark, run)
    assert len(out) > 0


@pytest.mark.perf_large
@pytest.mark.benchmark(group="large_point")
def test_perf_large_point_upstream(benchmark):
    _skip_if_missing("large_local")
    _, raster, points = _paths("large_local")

    def run():
        return fallback_point_query(points, raster, interpolate="bilinear")

    out = _run_benchmark(benchmark, run)
    assert len(out) > 0
