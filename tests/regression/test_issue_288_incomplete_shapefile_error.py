from __future__ import annotations

from pathlib import Path

import pytest

from rasterstats import zonal_stats

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_incomplete_shapefile_sidecars_raise_value_error(tmp_path):
    raster = DATA / "slope.tif"
    broken = tmp_path / "polygons.shp"
    broken.write_bytes((DATA / "polygons.shp").read_bytes())

    with pytest.raises(ValueError):
        zonal_stats(broken, raster)
