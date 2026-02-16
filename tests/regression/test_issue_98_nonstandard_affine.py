from __future__ import annotations

import numpy as np
from affine import Affine

from rasterstats import zonal_stats


def test_nonstandard_affine_transform_is_handled():
    data = np.array([[1, 2], [3, 4]], dtype=float)
    transform = Affine(2, 0.1, 0, 0.2, -2, 4)
    geom = {
        "type": "Polygon",
        "coordinates": [[(0, 4), (4.2, 4.4), (4.4, 0.4), (0.2, 0), (0, 4)]],
    }

    stats = zonal_stats([geom], data, affine=transform, stats=["count", "min", "max"])

    assert stats[0]["count"] >= 1
    assert stats[0]["max"] >= stats[0]["min"]
