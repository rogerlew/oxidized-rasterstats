from __future__ import annotations

from pathlib import Path

from rasterstats import zonal_stats
from rasterstats._fallback_py import fallback_zonal_stats

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_nodata_count_matches_upstream_for_non_overlapping_cells():
    polygons = DATA / "polygons_no_overlap.shp"
    raster = DATA / "slope_nodata.tif"

    stats = zonal_stats(polygons, raster, stats=["count", "nodata"], boundless=True)
    expected = fallback_zonal_stats(polygons, raster, stats=["count", "nodata"], boundless=True)

    assert stats == expected
    assert all(item["count"] == 0 for item in stats)
    assert all(item["nodata"] > 0 for item in stats)
