from __future__ import annotations

import inspect
import warnings

import pytest

import rasterstats


EXPECTED_EXPORTS = {
    "__version__",
    "cli",
    "gen_point_query",
    "gen_zonal_stats",
    "point_query",
    "raster_stats",
    "zonal_stats",
}


EXPECTED_SIGNATURES = {
    "zonal_stats": "(*args, **kwargs)",
    "raster_stats": "(*args, **kwargs)",
    "gen_zonal_stats": "(vectors, raster, layer=0, band=1, nodata=None, affine=None, stats=None, all_touched=False, categorical=False, category_map=None, add_stats=None, zone_func=None, raster_out=False, prefix=None, geojson_out=False, boundless=True, **kwargs)",
    "point_query": "(*args, **kwargs)",
    "gen_point_query": "(vectors, raster, band=1, layer=0, nodata=None, affine=None, interpolate='bilinear', property_name='value', geojson_out=False, boundless=True)",
}


def test_exports_match_upstream_contract():
    assert set(rasterstats.__all__) == EXPECTED_EXPORTS


@pytest.mark.parametrize("name,signature", EXPECTED_SIGNATURES.items())
def test_signatures_match(name, signature):
    assert str(inspect.signature(getattr(rasterstats, name))) == signature


def test_deprecated_raster_stats_warning():
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        try:
            rasterstats.raster_stats([], [[1]], affine=None)
        except Exception:
            pass
    assert any("alias to 'zonal_stats'" in str(w.message) for w in rec)
