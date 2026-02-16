from __future__ import annotations

import gc
import tracemalloc
from pathlib import Path

from rasterstats import zonal_stats

DATA = Path(__file__).resolve().parents[1] / "upstream" / "data"


def test_repeated_calls_do_not_show_unbounded_memory_growth():
    polygons = DATA / "polygons.shp"
    raster = DATA / "slope.tif"

    tracemalloc.start()
    baseline, _ = tracemalloc.get_traced_memory()

    for _ in range(120):
        zonal_stats(polygons, raster, stats=["mean"])

    gc.collect()
    current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert current - baseline < 8_000_000
