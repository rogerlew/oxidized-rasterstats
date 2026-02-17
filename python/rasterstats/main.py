from __future__ import annotations

import math
import warnings

from affine import Affine

from rasterstats._dispatch import dispatch_zonal_stats
from rasterstats._fallback_py import fallback_gen_zonal_stats

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - optional dependency
    tqdm = None


def _clean_inf(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _clean_inf(v) for k, v in value.items()}
    return value


def raster_stats(*args, **kwargs):
    """Deprecated. Use zonal_stats instead."""
    warnings.warn(
        "'raster_stats' is an alias to 'zonal_stats' and will disappear in 1.0",
        DeprecationWarning,
    )
    return zonal_stats(*args, **kwargs)


def zonal_stats(*args, **kwargs):
    """List-returning zonal stats API compatible with upstream rasterstats."""
    progress = kwargs.get("progress")
    if progress:
        if tqdm is None:
            raise ValueError(
                "You specified progress=True, but tqdm is not installed in "
                "the environment. "
                "You can do pip install rasterstats[progress] to install tqdm!"
            )
        stream = gen_zonal_stats(*args, **kwargs)
        total = None
        if args:
            try:
                total = len(args[0])
            except Exception:
                total = None
        return [stat for stat in tqdm(stream, total=total)]

    return list(gen_zonal_stats(*args, **kwargs))


def gen_zonal_stats(
    vectors,
    raster,
    layer=0,
    band=1,
    nodata=None,
    affine=None,
    stats=None,
    all_touched=False,
    categorical=False,
    category_map=None,
    add_stats=None,
    zone_func=None,
    raster_out=False,
    prefix=None,
    geojson_out=False,
    boundless=True,
    **kwargs,
):
    """Generator zonal stats API compatible with upstream rasterstats."""

    transform = kwargs.get("transform")
    if transform:
        warnings.warn(
            "GDAL-style transforms will disappear in 1.0. "
            "Use affine=Affine.from_gdal(*transform) instead",
            DeprecationWarning,
        )
        if affine is None:
            affine = Affine.from_gdal(*transform)

    cp = kwargs.get("copy_properties")
    if cp:
        warnings.warn("Use `geojson_out` to preserve feature properties", DeprecationWarning)

    band_num = kwargs.get("band_num")
    if band_num:
        warnings.warn("Use `band` to specify band number", DeprecationWarning)
        band = band_num

    fast = dispatch_zonal_stats(
        vectors,
        raster,
        layer=layer,
        band=band,
        nodata=nodata,
        stats=stats,
        all_touched=all_touched,
        categorical=categorical,
        category_map=category_map,
        add_stats=add_stats,
        zone_func=zone_func,
        raster_out=raster_out,
        prefix=prefix,
        geojson_out=geojson_out,
        boundless=boundless,
    )

    if fast is not None:
        for item in fast:
            yield _clean_inf(item)
        return

    fallback_records = list(
        fallback_gen_zonal_stats(
            vectors,
            raster,
            layer=layer,
            band=band,
            nodata=nodata,
            affine=affine,
            stats=stats,
            all_touched=all_touched,
            categorical=categorical,
            category_map=category_map,
            add_stats=add_stats,
            zone_func=zone_func,
            raster_out=raster_out,
            prefix=prefix,
            geojson_out=geojson_out,
            boundless=boundless,
            **kwargs,
        )
    )

    for item in fallback_records:
        yield _clean_inf(item)
