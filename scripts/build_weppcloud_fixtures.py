#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "dem/wbt/subcatchments.geojson",
    "dem/wbt/subcatchments.WGS.geojson",
    "dem/wbt/channels.geojson",
    "dem/wbt/channels.WGS.geojson",
    "dem/wbt/relief.tif",
    "dem/wbt/fvslop.tif",
    "dem/wbt/discha.tif",
    "dem/wbt/floaccum.tif",
    "dem/wbt/taspec.tif",
    "landuse/nlcd.tif",
    "watershed/hillslopes.parquet",
]


def run_json_command(cmd: list[str]) -> dict | None:
    try:
        out = subprocess.check_output(cmd, text=True)
    except Exception:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def validate_source(run_dir: Path) -> list[str]:
    missing = []
    for rel in REQUIRED_FILES:
        if not (run_dir / rel).exists():
            missing.append(rel)
    return missing


def count_geojson_features(path: Path) -> int | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if data.get("type") == "FeatureCollection":
        return len(data.get("features", []))
    if data.get("type") == "Feature":
        return 1
    return None


def _ring_points(geometry: dict) -> list[tuple[float, float]]:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon":
        return [tuple(pt[:2]) for pt in coords[0]] if coords else []
    if gtype == "MultiPolygon" and coords:
        return [tuple(pt[:2]) for pt in coords[0][0]] if coords[0] else []
    return []


def _simple_centroid(points: Iterable[tuple[float, float]]) -> tuple[float, float] | None:
    points = list(points)
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def build_points_geojson(run_dir: Path, out_points_geojson: Path) -> dict:
    parquet_path = run_dir / "watershed/hillslopes.parquet"
    used_parquet = False
    centroids: list[tuple[float, float]] = []

    try:
        import pyarrow.parquet as pq  # type: ignore

        table = pq.read_table(str(parquet_path), columns=["centroid_lon", "centroid_lat"])
        lons = table.column("centroid_lon").to_pylist()
        lats = table.column("centroid_lat").to_pylist()
        for lon, lat in zip(lons, lats):
            if lon is None or lat is None:
                continue
            centroids.append((float(lon), float(lat)))
        used_parquet = True
    except Exception:
        source_geojson = run_dir / "dem/wbt/subcatchments.geojson"
        data = json.loads(source_geojson.read_text(encoding="utf-8"))
        for feat in data.get("features", []):
            geom = feat.get("geometry") or {}
            ring = _ring_points(geom)
            c = _simple_centroid(ring)
            if c is not None:
                centroids.append(c)

    features = [
        {
            "type": "Feature",
            "properties": {"id": idx},
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
        }
        for idx, (lon, lat) in enumerate(centroids)
    ]

    payload = {"type": "FeatureCollection", "features": features}
    out_points_geojson.parent.mkdir(parents=True, exist_ok=True)
    out_points_geojson.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    return {
        "point_count": len(features),
        "point_source": "hillslopes.parquet" if used_parquet else "subcatchments.geojson(centroid-fallback)",
    }


def raster_info(path: Path) -> dict:
    info = run_json_command(["gdalinfo", "-json", str(path)])
    if not info:
        return {"path": str(path), "info": "unavailable"}

    band0 = (info.get("bands") or [{}])[0]
    return {
        "path": str(path),
        "size": info.get("size"),
        "crs": (info.get("coordinateSystem") or {}).get("wkt", "")[:120],
        "nodata": band0.get("noDataValue"),
        "dtype": band0.get("type"),
    }


def copy_fixture(run_dir: Path, out_root: Path, tier: str, manifests_dir: Path) -> dict:
    tier_out = out_root / tier
    tier_out.mkdir(parents=True, exist_ok=True)

    copied_files = []
    for rel in REQUIRED_FILES:
        src = run_dir / rel
        dst = tier_out / rel
        copy_file(src, dst)
        copied_files.append(rel)

    points_meta = build_points_geojson(run_dir, tier_out / "watershed/hillslope_points.geojson")

    geojson_counts = {}
    for rel in [
        "dem/wbt/subcatchments.geojson",
        "dem/wbt/subcatchments.WGS.geojson",
        "dem/wbt/channels.geojson",
        "dem/wbt/channels.WGS.geojson",
    ]:
        geojson_counts[rel] = count_geojson_features(tier_out / rel)

    rasters = {}
    for rel in [
        "dem/wbt/relief.tif",
        "dem/wbt/fvslop.tif",
        "dem/wbt/discha.tif",
        "dem/wbt/floaccum.tif",
        "dem/wbt/taspec.tif",
        "landuse/nlcd.tif",
    ]:
        rasters[rel] = raster_info(tier_out / rel)

    manifest = {
        "tier": tier,
        "source_run": str(run_dir),
        "copied_files": copied_files,
        "geojson_feature_counts": geojson_counts,
        "rasters": rasters,
        "points": points_meta,
    }

    manifests_dir.mkdir(parents=True, exist_ok=True)
    (manifests_dir / f"{tier}.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reproducible WEPPcloud fixtures")
    parser.add_argument("--small-run", type=Path, required=True)
    parser.add_argument("--large-run", type=Path, required=False)
    parser.add_argument("--out", type=Path, default=Path("tests/fixtures/weppcloud"))
    parser.add_argument(
        "--profile",
        choices=["ci-small", "local-large", "all"],
        default="all",
    )
    args = parser.parse_args()

    out_root = (ROOT / args.out).resolve() if not args.out.is_absolute() else args.out
    manifests_dir = out_root / "manifests"
    results = {"built": [], "skipped": []}

    if args.profile in {"ci-small", "all"}:
        small_run = args.small_run.resolve()
        missing = validate_source(small_run)
        if missing:
            raise SystemExit(
                f"small fixture source missing required files in {small_run}: {missing}"
            )
        manifest = copy_fixture(small_run, out_root, "small", manifests_dir)
        results["built"].append(manifest)

    if args.profile in {"local-large", "all"}:
        if not args.large_run:
            results["skipped"].append(
                {"tier": "large_local", "reason": "--large-run not provided"}
            )
        else:
            large_run = args.large_run.resolve()
            if not large_run.exists():
                results["skipped"].append(
                    {
                        "tier": "large_local",
                        "reason": f"source unavailable: {large_run}",
                    }
                )
            else:
                missing = validate_source(large_run)
                if missing:
                    results["skipped"].append(
                        {
                            "tier": "large_local",
                            "reason": f"missing required files: {missing}",
                        }
                    )
                else:
                    manifest = copy_fixture(large_run, out_root, "large_local", manifests_dir)
                    results["built"].append(manifest)

    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
