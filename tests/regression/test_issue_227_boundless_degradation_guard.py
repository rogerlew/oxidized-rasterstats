from __future__ import annotations

import time
from pathlib import Path

from rasterstats import zonal_stats
from rasterstats.io import read_features

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_boundless_many_features_completes_without_pathological_slowdown():
    raster = DATA / "slope.tif"
    seed_feature = next(read_features(DATA / "polygons_no_overlap.shp"))
    features = [seed_feature for _ in range(150)]

    start = time.perf_counter()
    out = zonal_stats(features, raster, boundless=True, stats=["count"])
    elapsed = time.perf_counter() - start

    assert len(out) == 150
    assert elapsed < 10
