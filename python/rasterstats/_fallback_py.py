"""Pure-Python compatibility fallback layer copied from upstream."""

from rasterstats._upstream_main import gen_zonal_stats as fallback_gen_zonal_stats
from rasterstats._upstream_main import raster_stats as fallback_raster_stats
from rasterstats._upstream_main import zonal_stats as fallback_zonal_stats
from rasterstats._upstream_point import gen_point_query as fallback_gen_point_query
from rasterstats._upstream_point import point_query as fallback_point_query

__all__ = [
    "fallback_gen_point_query",
    "fallback_gen_zonal_stats",
    "fallback_point_query",
    "fallback_raster_stats",
    "fallback_zonal_stats",
]
