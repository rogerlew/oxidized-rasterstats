from __future__ import annotations

from pathlib import Path

from rasterstats import point_query

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_bilinear_near_nodata_boundary_falls_back_safely():
    raster_nodata = DATA / "slope_nodata.tif"
    point = "POINT(245905 1000361)"

    nearest = point_query(point, raster_nodata, interpolate="nearest")[0]
    bilinear = point_query(point, raster_nodata, interpolate="bilinear")[0]

    assert nearest is not None
    assert bilinear is not None
    assert round(nearest) == round(bilinear) == 43
