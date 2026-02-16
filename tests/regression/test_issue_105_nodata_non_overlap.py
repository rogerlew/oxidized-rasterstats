from __future__ import annotations

from pathlib import Path

from rasterstats import zonal_stats

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_nodata_does_not_include_non_overlapping_cells():
    polygons = DATA / "polygons_no_overlap.shp"
    raster = DATA / "slope_nodata.tif"

    stats = zonal_stats(polygons, raster, stats=["count", "nodata"], boundless=True)

    assert stats[0]["count"] == 0
    assert stats[0]["nodata"] == 0
