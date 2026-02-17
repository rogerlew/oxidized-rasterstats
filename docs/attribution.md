# Attribution and Upstream Credit

This project derives significant compatibility-layer code, test fixtures, and
test suites from upstream
[`python-rasterstats`](https://github.com/perrygeo/python-rasterstats).

## Upstream Project

- Name: `python-rasterstats`
- Primary upstream author: Matthew Perry
- Upstream repository: <https://github.com/perrygeo/python-rasterstats>

## Where Upstream Material Is Used

- `vendor/upstream_rasterstats/`: vendored upstream source and tests at a pinned SHA.
- `tests/upstream/`: imported/adapted upstream parity tests and fixtures.
- `python/rasterstats/_upstream_main.py`: upstream-derived zonal implementation baseline.
- `python/rasterstats/_upstream_point.py`: upstream-derived point-query implementation baseline.
- `python/rasterstats/io.py`, `python/rasterstats/utils.py`, `python/rasterstats/cli.py`:
  compatibility modules synced from upstream and adapted for this package layout.

Pinned upstream commit is recorded in `vendor/upstream_rasterstats/SHA.txt`.
Upstream license text is preserved in `vendor/upstream_rasterstats/LICENSE.txt`.
Component-level ownership notes are documented in `NOTICE.md`.

## License Note

Upstream `python-rasterstats` is distributed under a BSD 3-Clause license with
copyright notices including:

- Copyright (c) 2013 Matthew Perry

When redistributing this project, preserve upstream attribution and license
notices for upstream-derived files.

## Project Artifact Ownership

- New Rust implementation and project-authored artifacts are credited to Roger
  Lew (see `NOTICE.md`).
- Upstream-derived compatibility material remains attributed to Matthew Perry
  and contributors.
