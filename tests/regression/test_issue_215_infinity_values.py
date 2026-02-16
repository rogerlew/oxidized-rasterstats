from __future__ import annotations

import math

import numpy as np
from affine import Affine

from rasterstats import zonal_stats


def test_infinite_values_are_not_emitted_in_stats():
    arr = np.array([[1.0, np.inf], [2.0, 3.0]], dtype=float)
    affine = Affine(1, 0, 0, 0, -1, 2)
    polygon = {
        "type": "Polygon",
        "coordinates": [[(0, 2), (2, 2), (2, 0), (0, 0), (0, 2)]],
    }

    stats = zonal_stats([polygon], arr, affine=affine, stats=["count", "mean", "max", "min"])
    for value in stats[0].values():
        if isinstance(value, float):
            assert math.isfinite(value)
