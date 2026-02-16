from __future__ import annotations

from rasterstats._dispatch import dispatch_point_query
from rasterstats._fallback_py import fallback_gen_point_query
from rasterstats._upstream_point import bilinear, geom_xys, point_window_unitxy


def point_query(*args, **kwargs):
    """List-returning point query API compatible with upstream rasterstats."""
    return list(gen_point_query(*args, **kwargs))


def gen_point_query(
    vectors,
    raster,
    band=1,
    layer=0,
    nodata=None,
    affine=None,
    interpolate="bilinear",
    property_name="value",
    geojson_out=False,
    boundless=True,
):
    """Generator point query API compatible with upstream rasterstats."""

    fast = dispatch_point_query(
        vectors,
        raster,
        band=band,
        layer=layer,
        nodata=nodata,
        interpolate=interpolate,
        geojson_out=geojson_out,
        boundless=boundless,
    )
    if fast is not None:
        for item in fast:
            yield item
        return

    for item in fallback_gen_point_query(
        vectors,
        raster,
        band=band,
        layer=layer,
        nodata=nodata,
        affine=affine,
        interpolate=interpolate,
        property_name=property_name,
        geojson_out=geojson_out,
        boundless=boundless,
    ):
        yield item
