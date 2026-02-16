mod errors;
mod geom;
mod point;
mod raster;
mod stats;
mod zonal;

use pyo3::prelude::*;
use pyo3::types::PyDict;

fn default_stats() -> Vec<String> {
    vec![
        "count".to_string(),
        "min".to_string(),
        "max".to_string(),
        "mean".to_string(),
    ]
}

#[pyfunction]
fn healthcheck() -> PyResult<&'static str> {
    Ok("ok")
}

#[pyfunction]
#[pyo3(signature = (
    vector_path,
    raster_path,
    layer=0,
    band=1,
    nodata=None,
    all_touched=false,
    boundless=true,
    stats=None,
))]
fn zonal_stats_path(
    py: Python<'_>,
    vector_path: &str,
    raster_path: &str,
    layer: usize,
    band: isize,
    nodata: Option<f64>,
    all_touched: bool,
    boundless: bool,
    stats: Option<Vec<String>>,
) -> PyResult<Vec<PyObject>> {
    let stat_list = stats.unwrap_or_else(default_stats);
    let records = zonal::zonal_stats_path(
        vector_path,
        raster_path,
        layer,
        band,
        nodata,
        all_touched,
        boundless,
        &stat_list,
    )?;

    let mut out = Vec::with_capacity(records.len());
    for record in records {
        let result = PyDict::new(py);
        for (k, v) in record.ints {
            result.set_item(k, v)?;
        }
        for (k, v) in record.floats {
            match v {
                Some(x) => result.set_item(k, x)?,
                None => result.set_item(k, py.None())?,
            }
        }
        out.push(result.into_py(py));
    }

    Ok(out)
}

#[pyfunction]
#[pyo3(signature = (
    raster_path,
    coords,
    band=1,
    nodata=None,
    interpolate="bilinear",
    boundless=true,
))]
fn point_query_path(
    raster_path: &str,
    coords: Vec<(f64, f64)>,
    band: isize,
    nodata: Option<f64>,
    interpolate: &str,
    boundless: bool,
) -> PyResult<Vec<Option<f64>>> {
    point::point_query_path(raster_path, &coords, band, nodata, interpolate, boundless)
        .map_err(Into::into)
}

#[pymodule]
fn _rs(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(healthcheck, m)?)?;
    m.add_function(wrap_pyfunction!(zonal_stats_path, m)?)?;
    m.add_function(wrap_pyfunction!(point_query_path, m)?)?;
    Ok(())
}
