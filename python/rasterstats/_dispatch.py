from __future__ import annotations

import json
import logging
import os
import tempfile
from os import PathLike
from typing import Any

import numpy as np
from shapely.geometry import shape

from rasterstats.io import read_features
from rasterstats.utils import check_stats
from rasterstats._upstream_point import geom_xys

try:
    from rasterstats import _rs as _rs_mod
except Exception:  # pragma: no cover - extension may be unavailable in pure-python runs
    _rs_mod = None

_LOG = logging.getLogger(__name__)


_SUPPORTED_STATS = {
    "min",
    "max",
    "mean",
    "count",
    "sum",
    "std",
    "median",
    "majority",
    "minority",
    "unique",
    "range",
    "nodata",
    "nan",
}


def _rust_globally_disabled() -> bool:
    return os.environ.get("OXRS_DISABLE_RUST", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _rust_available_default_on() -> bool:
    return _rs_mod is not None and not _rust_globally_disabled()


def _is_pathlike(value: Any) -> bool:
    return isinstance(value, (str, PathLike))


def _sanitize_inf(record: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for key, value in record.items():
        if isinstance(value, float) and not np.isfinite(value):
            cleaned[key] = None
        else:
            cleaned[key] = value
    return cleaned


def _warn_fallback(api: str, stage: str, err: Exception) -> None:
    _LOG.warning(
        "Rust dispatch fallback for %s at %s: %s",
        api,
        stage,
        err,
        exc_info=err,
    )


def dispatch_zonal_stats(
    vectors: Any,
    raster: Any,
    *,
    layer: Any,
    band: int,
    nodata: float | None,
    stats: Any,
    all_touched: bool,
    categorical: bool,
    category_map: dict | None,
    add_stats: dict | None,
    zone_func: Any,
    raster_out: bool,
    prefix: str | None,
    geojson_out: bool,
    boundless: bool,
) -> list[dict[str, Any]] | None:
    if not _rust_available_default_on():
        return None

    if not _is_pathlike(raster):
        return None

    if categorical or category_map is not None:
        return None

    if add_stats is not None or zone_func is not None or raster_out or geojson_out:
        return None

    if not isinstance(layer, int):
        return None

    norm_stats, _ = check_stats(stats, categorical)
    if not all(s in _SUPPORTED_STATS or s.startswith("percentile_") for s in norm_stats):
        return None

    raster_path = str(raster)
    if not os.path.exists(raster_path):
        return None

    temp_vector_path: str | None = None
    if _is_pathlike(vectors):
        vector_path = str(vectors)
        if not os.path.exists(vector_path):
            return None
        vector_layer = layer
    else:
        # Normalize in-memory/iterable features through a temporary GeoJSON so
        # Rust and Python input forms produce identical semantics.
        try:
            features = list(read_features(vectors, layer=layer))
            if not features:
                return []
            payload = {"type": "FeatureCollection", "features": features}
            tmp_path: str | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".geojson", delete=False
                ) as tmp:
                    tmp_path = tmp.name
                    json.dump(payload, tmp)
                temp_vector_path = tmp_path
            except Exception as exc:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                _warn_fallback("zonal_stats", "feature_serialization", exc)
                return None
        except Exception as exc:
            _warn_fallback("zonal_stats", "feature_normalization", exc)
            return None
        vector_path = temp_vector_path
        vector_layer = 0

    try:
        result = _rs_mod.zonal_stats_path(
            vector_path,
            raster_path,
            layer=vector_layer,
            band=band,
            nodata=nodata,
            all_touched=all_touched,
            boundless=boundless,
            stats=list(norm_stats),
        )
    except Exception as exc:
        _warn_fallback("zonal_stats", "rust_call", exc)
        return None
    finally:
        if temp_vector_path:
            try:
                os.unlink(temp_vector_path)
            except OSError:
                pass

    prefixed = []
    for item in result:
        rec = dict(item)
        rec = _sanitize_inf(rec)
        if prefix:
            rec = {f"{prefix}{k}": v for k, v in rec.items()}
        prefixed.append(rec)
    return prefixed


def dispatch_point_query(
    vectors: Any,
    raster: Any,
    *,
    band: int,
    layer: Any,
    nodata: float | None,
    interpolate: str,
    geojson_out: bool,
    boundless: bool,
) -> list[Any] | None:
    if not _rust_available_default_on():
        return None

    if not _is_pathlike(vectors) or not _is_pathlike(raster):
        return None

    if geojson_out:
        return None

    if not boundless:
        return None

    if not isinstance(layer, int):
        return None

    raster_path = str(raster)
    if not os.path.exists(raster_path):
        return None

    features = list(read_features(vectors, layer))
    if not features:
        return []

    coords: list[tuple[float, float]] = []
    counts: list[int] = []
    for feat in features:
        geom = shape(feat["geometry"])
        pts = [(float(x), float(y)) for x, y in geom_xys(geom)]
        counts.append(len(pts))
        coords.extend(pts)

    try:
        raw = _rs_mod.point_query_path(
            raster_path,
            coords,
            band=band,
            nodata=nodata,
            interpolate=interpolate,
            boundless=boundless,
        )
    except Exception as exc:
        _warn_fallback("point_query", "rust_call", exc)
        return None

    out: list[Any] = []
    idx = 0
    for count in counts:
        vals = raw[idx : idx + count]
        idx += count
        if count == 1:
            out.append(vals[0])
        else:
            out.append(vals)
    return out
