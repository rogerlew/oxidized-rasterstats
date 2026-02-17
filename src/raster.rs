use crate::errors::{OxrsError, OxrsResult};
use gdal::raster::Buffer;
use gdal::Dataset;
use std::path::Path;

#[derive(Clone, Copy, Debug)]
pub struct Window {
    pub row_start: isize,
    pub row_end: isize,
    pub col_start: isize,
    pub col_end: isize,
}

pub struct RasterContext {
    dataset: Dataset,
    band_index: usize,
    pub nodata: Option<f64>,
    geotransform: [f64; 6],
    inverse_geotransform: [f64; 6],
    width: usize,
    height: usize,
}

impl RasterContext {
    pub fn open(path: &str, band: isize, nodata: Option<f64>) -> OxrsResult<Self> {
        if band < 1 {
            return Err(OxrsError::InvalidArgument(
                "band must be >= 1".to_string(),
            ));
        }
        let band_index = usize::try_from(band).map_err(|_| {
            OxrsError::InvalidArgument("band must be a positive integer".to_string())
        })?;

        let dataset = Dataset::open(Path::new(path))?;
        let raster_band = dataset.rasterband(band_index)?;
        let source_nodata = nodata.or_else(|| raster_band.no_data_value());
        let geotransform = dataset.geo_transform()?;
        let inverse_geotransform = invert_geo_transform(geotransform).ok_or_else(|| {
            OxrsError::Runtime("unable to invert raster geotransform".to_string())
        })?;

        Ok(Self {
            width: raster_band.x_size(),
            height: raster_band.y_size(),
            dataset,
            band_index,
            nodata: source_nodata,
            geotransform,
            inverse_geotransform,
        })
    }

    pub fn world_to_pixel(&self, x: f64, y: f64) -> (f64, f64) {
        let gt = self.inverse_geotransform;
        let col = gt[0] + gt[1] * x + gt[2] * y;
        let row = gt[3] + gt[4] * x + gt[5] * y;
        (col, row)
    }

    pub fn is_inside(&self, row: isize, col: isize) -> bool {
        row >= 0
            && row < self.height as isize
            && col >= 0
            && col < self.width as isize
    }

    pub fn read_value(&self, row: isize, col: isize, boundless: bool) -> OxrsResult<Option<f64>> {
        if !self.is_inside(row, col) {
            if boundless {
                return Ok(None);
            }
            return Ok(None);
        }

        let raster_band = self.dataset.rasterband(self.band_index)?;
        let buffer: Buffer<f64> = raster_band.read_as((col, row), (1, 1), (1, 1), None)?;
        let value = buffer.data().first().copied();

        Ok(match value {
            None => None,
            Some(v) if !v.is_finite() => None,
            Some(v) => {
                if self
                    .nodata
                    .map(|n| (v - n).abs() <= f64::EPSILON)
                    .unwrap_or(false)
                {
                    None
                } else {
                    Some(v)
                }
            }
        })
    }

    pub fn window_for_bounds_unclipped(
        &self,
        min_x: f64,
        min_y: f64,
        max_x: f64,
        max_y: f64,
    ) -> Window {
        let corners = [
            self.world_to_pixel(min_x, min_y),
            self.world_to_pixel(min_x, max_y),
            self.world_to_pixel(max_x, min_y),
            self.world_to_pixel(max_x, max_y),
        ];

        let min_col = corners
            .iter()
            .map(|(c, _)| *c)
            .fold(f64::INFINITY, f64::min)
            .floor() as isize;
        let max_col = corners
            .iter()
            .map(|(c, _)| *c)
            .fold(f64::NEG_INFINITY, f64::max)
            .ceil() as isize;
        let min_row = corners
            .iter()
            .map(|(_, r)| *r)
            .fold(f64::INFINITY, f64::min)
            .floor() as isize;
        let max_row = corners
            .iter()
            .map(|(_, r)| *r)
            .fold(f64::NEG_INFINITY, f64::max)
            .ceil() as isize;

        Window {
            row_start: min_row,
            row_end: max_row,
            col_start: min_col,
            col_end: max_col,
        }
    }

    pub fn window_geo_transform(&self, window: Window) -> [f64; 6] {
        let gt = self.geotransform;
        let col_off = window.col_start as f64;
        let row_off = window.row_start as f64;
        [
            gt[0] + (col_off * gt[1]) + (row_off * gt[2]),
            gt[1],
            gt[2],
            gt[3] + (col_off * gt[4]) + (row_off * gt[5]),
            gt[4],
            gt[5],
        ]
    }

    pub fn read_window_f64_boundless(
        &self,
        window: Window,
        boundless: bool,
        fill_nodata: f64,
    ) -> OxrsResult<(usize, usize, Vec<f64>)> {
        if window.row_end < window.row_start || window.col_end < window.col_start {
            return Ok((0, 0, Vec::new()));
        }

        if self.window_beyond_extent(window) && !boundless {
            return Err(OxrsError::InvalidArgument(
                "Window/bounds is outside dataset extent, boundless reads are disabled"
                    .to_string(),
            ));
        }

        let width = (window.col_end - window.col_start + 1) as usize;
        let height = (window.row_end - window.row_start + 1) as usize;
        let mut out = vec![fill_nodata; width * height];

        let Some(overlap) = self.clip_window(window) else {
            return Ok((width, height, out));
        };

        let overlap_width = (overlap.col_end - overlap.col_start + 1) as usize;
        let overlap_height = (overlap.row_end - overlap.row_start + 1) as usize;
        let raster_band = self.dataset.rasterband(self.band_index)?;
        let overlap_buf: Buffer<f64> = raster_band.read_as(
            (overlap.col_start, overlap.row_start),
            (overlap_width, overlap_height),
            (overlap_width, overlap_height),
            None,
        )?;
        let (_, overlap_data) = overlap_buf.into_shape_and_vec();

        let dst_row_off = (overlap.row_start - window.row_start) as usize;
        let dst_col_off = (overlap.col_start - window.col_start) as usize;
        for r in 0..overlap_height {
            let src_start = r * overlap_width;
            let src_end = src_start + overlap_width;
            let dst_start = (dst_row_off + r) * width + dst_col_off;
            let dst_end = dst_start + overlap_width;
            out[dst_start..dst_end].copy_from_slice(&overlap_data[src_start..src_end]);
        }

        Ok((width, height, out))
    }

    pub fn window_beyond_extent(&self, window: Window) -> bool {
        window.row_start < 0
            || window.col_start < 0
            || window.row_end >= self.height as isize
            || window.col_end >= self.width as isize
    }

    pub fn clip_window(&self, window: Window) -> Option<Window> {
        let clipped = Window {
            row_start: window.row_start.max(0),
            row_end: window.row_end.min((self.height as isize) - 1),
            col_start: window.col_start.max(0),
            col_end: window.col_end.min((self.width as isize) - 1),
        };
        if clipped.row_end < clipped.row_start || clipped.col_end < clipped.col_start {
            None
        } else {
            Some(clipped)
        }
    }
}

fn invert_geo_transform(gt: [f64; 6]) -> Option<[f64; 6]> {
    let det = gt[1] * gt[5] - gt[2] * gt[4];
    if det.abs() < 1e-15 {
        return None;
    }

    let inv_det = 1.0 / det;
    Some([
        (gt[2] * gt[3] - gt[0] * gt[5]) * inv_det,
        gt[5] * inv_det,
        -gt[2] * inv_det,
        (gt[0] * gt[4] - gt[1] * gt[3]) * inv_det,
        -gt[4] * inv_det,
        gt[1] * inv_det,
    ])
}
