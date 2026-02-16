from __future__ import annotations

from pathlib import Path

from rasterstats import zonal_stats

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_empty_zone_has_zero_count_and_zero_nodata():
    polygons = DATA / "polygons_no_overlap.shp"
    raster = DATA / "slope.tif"

    stats = zonal_stats(polygons, raster, stats=["count", "nodata"])

    assert stats[0]["count"] == 0
    assert stats[0]["nodata"] == 0
