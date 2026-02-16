use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::PyErr;

#[derive(thiserror::Error, Debug)]
pub enum OxrsError {
    #[error("invalid argument: {0}")]
    InvalidArgument(String),
    #[error("GDAL error: {0}")]
    Gdal(String),
    #[error("runtime error: {0}")]
    Runtime(String),
}

impl From<gdal::errors::GdalError> for OxrsError {
    fn from(value: gdal::errors::GdalError) -> Self {
        Self::Gdal(value.to_string())
    }
}

impl From<anyhow::Error> for OxrsError {
    fn from(value: anyhow::Error) -> Self {
        Self::Runtime(value.to_string())
    }
}

impl From<OxrsError> for PyErr {
    fn from(value: OxrsError) -> Self {
        match value {
            OxrsError::InvalidArgument(msg) => PyValueError::new_err(msg),
            OxrsError::Gdal(msg) | OxrsError::Runtime(msg) => PyRuntimeError::new_err(msg),
        }
    }
}

pub type OxrsResult<T> = Result<T, OxrsError>;
