from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "weppcloud"


def _load_manifest(name: str) -> dict:
    path = ROOT / "manifests" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_small_manifest_schema_and_counts():
    manifest = _load_manifest("small")
    assert manifest["tier"] == "small"
    assert manifest["geojson_feature_counts"]["dem/wbt/subcatchments.geojson"] > 0
    assert manifest["points"]["point_count"] > 0

    points_path = ROOT / "small" / "watershed" / "hillslope_points.geojson"
    points = json.loads(points_path.read_text(encoding="utf-8"))
    assert len(points["features"]) == manifest["points"]["point_count"]


def test_large_manifest_schema_if_available():
    manifest_path = ROOT / "manifests" / "large_local.json"
    if not manifest_path.exists():
        pytest.skip("large_local manifest not available")
    manifest = _load_manifest("large_local")
    assert manifest["tier"] == "large_local"
    assert manifest["geojson_feature_counts"]["dem/wbt/subcatchments.geojson"] >= 1000
