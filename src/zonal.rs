use crate::errors::OxrsResult;
use crate::raster::RasterContext;
use crate::stats::{compute_stats, StatRecord};
use gdal::raster::{rasterize, Buffer, RasterizeOptions};
use gdal::vector::LayerAccess;
use gdal::{Dataset, DriverManager};
use std::path::Path;

pub fn zonal_stats_path(
    vectors_path: &str,
    raster_path: &str,
    layer_index: usize,
    band: isize,
    nodata: Option<f64>,
    all_touched: bool,
    boundless: bool,
    stats: &[String],
) -> OxrsResult<Vec<StatRecord>> {
    let raster = RasterContext::open(raster_path, band, nodata)?;
    let vectors = Dataset::open(Path::new(vectors_path))?;
    let mut layer = vectors.layer(layer_index)?;
    let mem_driver = DriverManager::get_driver_by_name("MEM")?;
    let mut out = Vec::new();

    for feature in layer.features() {
        let Some(geom) = feature.geometry() else {
            out.push(compute_stats(&[], stats, 0, 0));
            continue;
        };

        let env = geom.envelope();
        let window = raster.window_for_bounds_unclipped(env.MinX, env.MinY, env.MaxX, env.MaxY);

        if window.row_end < window.row_start || window.col_end < window.col_start {
            out.push(compute_stats(&[], stats, 0, 0));
            continue;
        }

        let effective_nodata = raster.nodata.unwrap_or(-999.0);
        let (width, height, values_window) =
            raster.read_window_f64_boundless(window, boundless, effective_nodata)?;
        if width == 0 || height == 0 {
            out.push(compute_stats(&[], stats, 0, 0));
            continue;
        }

        let mut mask_ds = mem_driver.create_with_band_type::<u8, _>("", width, height, 1)?;
        let window_gt = raster.window_geo_transform(window);
        mask_ds.set_geo_transform(&window_gt)?;
        {
            let mut mask_band = mask_ds.rasterband(1)?;
            mask_band.fill(0.0, None)?;
        }

        let burn_values = [1.0_f64];
        let geoms = [geom.clone()];
        rasterize(
            &mut mask_ds,
            &[1],
            &geoms,
            &burn_values,
            Some(RasterizeOptions {
                all_touched,
                ..Default::default()
            }),
        )?;
        let mask_band = mask_ds.rasterband(1)?;
        let mask_buf: Buffer<u8> = mask_band.read_as((0, 0), (width, height), (width, height), None)?;
        let (_, mask_window) = mask_buf.into_shape_and_vec();

        let mut values = Vec::new();
        let mut nodata_count: usize = 0;
        let mut nan_count: usize = 0;

        for (mask, value) in mask_window.iter().zip(values_window.iter()) {
            if *mask == 0 {
                continue;
            }
            let v = *value;
            if (v - effective_nodata).abs() <= f64::EPSILON {
                nodata_count += 1;
            } else if !v.is_finite() {
                nan_count += 1;
            } else {
                values.push(v);
            }
        }

        out.push(compute_stats(&values, stats, nodata_count, nan_count));
    }

    Ok(out)
}
