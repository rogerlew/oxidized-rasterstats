from __future__ import annotations

from pathlib import Path

import rasterstats.main as rs_main
from rasterstats import zonal_stats
from rasterstats.io import read_features

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_progress_handles_unsized_iterable(monkeypatch):
    polygons = DATA / "polygons.shp"
    raster = DATA / "slope.tif"

    def passthrough_tqdm(iterable, total=None):
        assert total is None
        return iterable

    monkeypatch.setattr(rs_main, "tqdm", passthrough_tqdm)

    unsized = (feature for feature in read_features(polygons))
    result = zonal_stats(unsized, raster, progress=True)

    assert len(result) == 2
    assert result[0]["count"] == 75
