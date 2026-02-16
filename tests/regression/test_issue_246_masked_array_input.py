from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from rasterstats import zonal_stats

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_masked_array_input_is_supported():
    polygons = DATA / "polygons.shp"
    raster = DATA / "slope.tif"

    with rasterio.open(raster) as src:
        arr = src.read(1)
        affine = src.transform

    masked = np.ma.masked_array(arr, mask=arr < 0)
    result = zonal_stats(polygons, masked, affine=affine, stats=["count", "min", "max"])

    assert len(result) == 2
    assert result[0]["count"] > 0
    assert result[0]["max"] >= result[0]["min"]
