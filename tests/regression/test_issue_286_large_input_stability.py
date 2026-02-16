from __future__ import annotations

from pathlib import Path

from rasterstats import zonal_stats
from rasterstats.io import read_features

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_large_feature_batch_completes_without_crash():
    raster = DATA / "slope.tif"
    feature = next(read_features(DATA / "polygons.shp"))
    features = [feature for _ in range(1000)]

    stats = zonal_stats(features, raster, stats=["count"])

    assert len(stats) == 1000
    assert all(item["count"] >= 0 for item in stats)
