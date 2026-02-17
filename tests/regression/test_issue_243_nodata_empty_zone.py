from __future__ import annotations

from pathlib import Path

from rasterstats import zonal_stats
from rasterstats._fallback_py import fallback_zonal_stats

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_empty_zone_nodata_footprint_matches_upstream():
    polygons = DATA / "polygons_no_overlap.shp"
    raster = DATA / "slope.tif"

    stats = zonal_stats(polygons, raster, stats=["count", "nodata"])
    expected = fallback_zonal_stats(polygons, raster, stats=["count", "nodata"])

    assert stats == expected
    assert all(item["count"] == 0 for item in stats)
    assert all(item["nodata"] > 0 for item in stats)
