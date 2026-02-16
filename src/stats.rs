use std::cmp::Ordering;
use std::collections::{BTreeMap, HashMap};

#[derive(Debug, Clone)]
pub struct StatRecord {
    pub floats: BTreeMap<String, Option<f64>>,
    pub ints: BTreeMap<String, i64>,
}

impl StatRecord {
    pub fn new() -> Self {
        Self {
            floats: BTreeMap::new(),
            ints: BTreeMap::new(),
        }
    }
}

fn sort_values(values: &[f64]) -> Vec<f64> {
    let mut sorted = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));
    sorted
}

fn percentile(sorted: &[f64], q: f64) -> f64 {
    if sorted.is_empty() {
        return f64::NAN;
    }
    if sorted.len() == 1 {
        return sorted[0];
    }
    let q = q.clamp(0.0, 100.0);
    let n = sorted.len() as f64;
    let pos = (q / 100.0) * (n - 1.0);
    let low = pos.floor() as usize;
    let high = pos.ceil() as usize;
    if low == high {
        sorted[low]
    } else {
        let weight = pos - (low as f64);
        (sorted[low] * (1.0 - weight)) + (sorted[high] * weight)
    }
}

fn histogram(values: &[f64]) -> HashMap<u64, usize> {
    let mut map = HashMap::new();
    for v in values {
        *map.entry(v.to_bits()).or_insert(0) += 1;
    }
    map
}

fn mode_value(values: &[f64], majority: bool) -> Option<f64> {
    if values.is_empty() {
        return None;
    }
    let hist = histogram(values);
    let mut selected: Option<(u64, usize)> = None;
    for (bits, count) in hist {
        selected = match selected {
            None => Some((bits, count)),
            Some((prev_bits, prev_count)) => {
                let better = if majority {
                    count > prev_count || (count == prev_count && bits < prev_bits)
                } else {
                    count < prev_count || (count == prev_count && bits < prev_bits)
                };
                if better {
                    Some((bits, count))
                } else {
                    Some((prev_bits, prev_count))
                }
            }
        }
    }
    selected.map(|(bits, _)| f64::from_bits(bits))
}

pub fn compute_stats(
    values: &[f64],
    stats: &[String],
    nodata_count: usize,
    nan_count: usize,
) -> StatRecord {
    let mut record = StatRecord::new();

    if values.is_empty() {
        for stat in stats {
            if stat == "count" {
                record.ints.insert(stat.clone(), 0);
            } else if stat == "nodata" {
                record.floats.insert(stat.clone(), Some(nodata_count as f64));
            } else if stat == "nan" {
                record.floats.insert(stat.clone(), Some(nan_count as f64));
            } else {
                record.floats.insert(stat.clone(), None);
            }
        }
        return record;
    }

    let sorted = sort_values(values);
    let count = values.len() as i64;
    let sum: f64 = values.iter().sum();
    let mean = sum / (count as f64);
    let min = *sorted.first().unwrap_or(&f64::NAN);
    let max = *sorted.last().unwrap_or(&f64::NAN);

    for stat in stats {
        match stat.as_str() {
            "min" => {
                record.floats.insert(stat.clone(), Some(min));
            }
            "max" => {
                record.floats.insert(stat.clone(), Some(max));
            }
            "mean" => {
                record.floats.insert(stat.clone(), Some(mean));
            }
            "sum" => {
                record.floats.insert(stat.clone(), Some(sum));
            }
            "count" => {
                record.ints.insert(stat.clone(), count);
            }
            "std" => {
                let var = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (count as f64);
                record.floats.insert(stat.clone(), Some(var.sqrt()));
            }
            "median" => {
                let med = percentile(&sorted, 50.0);
                record.floats.insert(stat.clone(), Some(med));
            }
            "majority" => {
                record
                    .floats
                    .insert(stat.clone(), mode_value(values, true));
            }
            "minority" => {
                record
                    .floats
                    .insert(stat.clone(), mode_value(values, false));
            }
            "unique" => {
                let unique = histogram(values).len() as i64;
                record.ints.insert(stat.clone(), unique);
            }
            "range" => {
                record.floats.insert(stat.clone(), Some(max - min));
            }
            "nodata" => {
                record
                    .floats
                    .insert(stat.clone(), Some(nodata_count as f64));
            }
            "nan" => {
                record.floats.insert(stat.clone(), Some(nan_count as f64));
            }
            _ if stat.starts_with("percentile_") => {
                let q = stat
                    .split('_')
                    .last()
                    .and_then(|v| v.parse::<f64>().ok())
                    .unwrap_or(50.0);
                record
                    .floats
                    .insert(stat.clone(), Some(percentile(&sorted, q)));
            }
            _ => {
                record.floats.insert(stat.clone(), None);
            }
        }
    }

    record
}

#[cfg(test)]
mod tests {
    use super::compute_stats;

    #[test]
    fn stats_basics() {
        let stats = vec!["min".to_string(), "max".to_string(), "mean".to_string(), "count".to_string()];
        let rec = compute_stats(&[1.0, 2.0, 3.0], &stats, 0, 0);
        assert_eq!(rec.floats.get("min").copied().flatten(), Some(1.0));
        assert_eq!(rec.floats.get("max").copied().flatten(), Some(3.0));
        assert_eq!(rec.floats.get("mean").copied().flatten(), Some(2.0));
        assert_eq!(rec.ints.get("count").copied(), Some(3));
    }
}
