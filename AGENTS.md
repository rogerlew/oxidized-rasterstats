# AGENTS.md

## Scope

These instructions apply to the entire repository.

## Planning Policy

`codex_exec_plans.md` is retained as project history and reference material, but it is not the active source of truth for execution.

For implementation and validation work:

1. Follow direct user instructions and repository code/tests.
2. Use `codex_exec_plans.md` only when explicitly requested.

## Build and Test Policy

When running implementation work, run relevant local build/test commands and report pass/fail status.

If a step is blocked by missing environment/data, the agent must:

1. Continue with all unblocked steps.
2. Mark blocked steps explicitly as skipped with reason.
3. Report the skip in the work summary.

## Behavior Expectations

1. Preserve drop-in compatibility for import path `rasterstats`.
2. Use `maturin` for packaging/build workflows.
3. Use GDAL-backed Rust fast paths with Python fallback behavior.
4. Document significant interface or benchmark deviations in repository documentation.
