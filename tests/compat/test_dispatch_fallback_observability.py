from __future__ import annotations

import logging
from pathlib import Path

from rasterstats import point_query, zonal_stats
from rasterstats import _dispatch
from rasterstats._fallback_py import fallback_point_query, fallback_zonal_stats

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


class _BrokenRustModule:
    @staticmethod
    def zonal_stats_path(*_args, **_kwargs):
        raise RuntimeError("forced zonal rust failure")

    @staticmethod
    def point_query_path(*_args, **_kwargs):
        raise RuntimeError("forced point rust failure")


def test_zonal_dispatch_logs_warning_and_falls_back(monkeypatch, caplog):
    vectors = DATA / "polygons.shp"
    raster = DATA / "slope.tif"
    expected = fallback_zonal_stats(vectors, raster, stats=["count", "mean"])

    monkeypatch.delenv("OXRS_DISABLE_RUST", raising=False)
    monkeypatch.setattr(_dispatch, "_rs_mod", _BrokenRustModule())

    with caplog.at_level(logging.WARNING, logger="rasterstats._dispatch"):
        got = zonal_stats(vectors, raster, stats=["count", "mean"])

    assert got == expected
    assert any(
        "Rust dispatch fallback for zonal_stats at rust_call" in record.getMessage()
        for record in caplog.records
    )


def test_point_dispatch_logs_warning_and_falls_back(monkeypatch, caplog):
    vectors = DATA / "points.shp"
    raster = DATA / "slope.tif"
    expected = fallback_point_query(vectors, raster, interpolate="bilinear")

    monkeypatch.delenv("OXRS_DISABLE_RUST", raising=False)
    monkeypatch.setattr(_dispatch, "_rs_mod", _BrokenRustModule())

    with caplog.at_level(logging.WARNING, logger="rasterstats._dispatch"):
        got = point_query(vectors, raster, interpolate="bilinear")

    assert got == expected
    assert any(
        "Rust dispatch fallback for point_query at rust_call" in record.getMessage()
        for record in caplog.records
    )
