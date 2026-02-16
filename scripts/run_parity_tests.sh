#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=python pytest tests/upstream tests/compat -q "$@"
