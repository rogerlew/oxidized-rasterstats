use crate::errors::{OxrsError, OxrsResult};

pub fn require_finite(value: f64, name: &str) -> OxrsResult<f64> {
    if value.is_finite() {
        Ok(value)
    } else {
        Err(OxrsError::InvalidArgument(format!(
            "{name} must be finite"
        )))
    }
}
