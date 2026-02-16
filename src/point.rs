use crate::errors::{OxrsError, OxrsResult};
use crate::geom::require_finite;
use crate::raster::RasterContext;

fn bilinear(values: [[Option<f64>; 2]; 2], x: f64, y: f64) -> Option<f64> {
    if !(0.0..=1.0).contains(&x) || !(0.0..=1.0).contains(&y) {
        return None;
    }

    let ul = values[0][0];
    let ur = values[0][1];
    let ll = values[1][0];
    let lr = values[1][1];

    if ul.is_none() || ur.is_none() || ll.is_none() || lr.is_none() {
        let row = (1.0 - y).round() as usize;
        let col = x.round() as usize;
        return values.get(row).and_then(|r| r.get(col)).copied().flatten();
    }

    let ul = ul.unwrap_or_default();
    let ur = ur.unwrap_or_default();
    let ll = ll.unwrap_or_default();
    let lr = lr.unwrap_or_default();

    Some(
        (ll * (1.0 - x) * (1.0 - y))
            + (lr * x * (1.0 - y))
            + (ul * (1.0 - x) * y)
            + (ur * x * y),
    )
}

pub fn point_query_path(
    raster_path: &str,
    coords: &[(f64, f64)],
    band: isize,
    nodata: Option<f64>,
    interpolate: &str,
    boundless: bool,
) -> OxrsResult<Vec<Option<f64>>> {
    if interpolate != "nearest" && interpolate != "bilinear" {
        return Err(OxrsError::InvalidArgument(
            "interpolate must be nearest or bilinear".to_string(),
        ));
    }

    let raster = RasterContext::open(raster_path, band, nodata)?;
    let mut out = Vec::with_capacity(coords.len());

    for (x, y) in coords {
        let x = require_finite(*x, "x")?;
        let y = require_finite(*y, "y")?;
        let (fcol, frow) = raster.world_to_pixel(x, y);

        if interpolate == "nearest" {
            let row = frow.floor() as isize;
            let col = fcol.floor() as isize;
            out.push(raster.read_value(row, col, boundless)?);
            continue;
        }

        let r = frow.round() as isize;
        let c = fcol.round() as isize;
        let unitx = 0.5 - ((c as f64) - fcol);
        let unity = 0.5 + ((r as f64) - frow);

        let ul = raster.read_value(r - 1, c - 1, boundless)?;
        let ur = raster.read_value(r - 1, c, boundless)?;
        let ll = raster.read_value(r, c - 1, boundless)?;
        let lr = raster.read_value(r, c, boundless)?;
        out.push(bilinear([[ul, ur], [ll, lr]], unitx, unity));
    }

    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::bilinear;

    #[test]
    fn bilinear_interp() {
        let vals = [[Some(10.0), Some(20.0)], [Some(30.0), Some(40.0)]];
        let v = bilinear(vals, 0.5, 0.5).unwrap();
        assert!((v - 25.0).abs() < 1e-6);
    }
}
