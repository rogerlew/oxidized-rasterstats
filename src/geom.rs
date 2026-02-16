use crate::errors::{OxrsError, OxrsResult};
use gdal::vector::Geometry;

pub fn point_geometry(x: f64, y: f64) -> OxrsResult<Geometry> {
    Geometry::from_wkt(&format!("POINT ({x} {y})")).map_err(Into::into)
}

pub fn cell_polygon(corners: &[(f64, f64); 4]) -> OxrsResult<Geometry> {
    let (x1, y1) = corners[0];
    let (x2, y2) = corners[1];
    let (x3, y3) = corners[2];
    let (x4, y4) = corners[3];
    let wkt = format!(
        "POLYGON (({x1} {y1}, {x2} {y2}, {x3} {y3}, {x4} {y4}, {x1} {y1}))"
    );
    Geometry::from_wkt(&wkt).map_err(Into::into)
}

pub fn require_finite(value: f64, name: &str) -> OxrsResult<f64> {
    if value.is_finite() {
        Ok(value)
    } else {
        Err(OxrsError::InvalidArgument(format!(
            "{name} must be finite"
        )))
    }
}
