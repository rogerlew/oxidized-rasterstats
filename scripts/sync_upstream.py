#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def ensure_commit(repo: Path, sha: str) -> None:
    run(["git", "-C", str(repo), "cat-file", "-e", f"{sha}^{{commit}}"])


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and file_hash(src) == file_hash(dst):
        return False
    shutil.copy2(src, dst)
    return True


def copy_tree(src: Path, dst: Path) -> int:
    copied = 0
    for item in sorted(src.rglob("*")):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        copied += int(copy_file(item, target))
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync pinned upstream rasterstats snapshot")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    ensure_commit(repo, args.sha)

    vendor_dir = ROOT / "vendor" / "upstream_rasterstats"
    vendor_src = vendor_dir / "src" / "rasterstats"
    vendor_tests = vendor_dir / "tests"
    vendor_dir.mkdir(parents=True, exist_ok=True)

    upstream_src = repo / "src" / "rasterstats"
    upstream_tests = repo / "tests"

    copied_src = copy_tree(upstream_src, vendor_src)
    copied_tests = copy_tree(upstream_tests, vendor_tests)

    # Python compatibility modules.
    py_pkg = ROOT / "python" / "rasterstats"
    py_pkg.mkdir(parents=True, exist_ok=True)
    copy_file(upstream_src / "io.py", py_pkg / "io.py")
    copy_file(upstream_src / "utils.py", py_pkg / "utils.py")
    copy_file(upstream_src / "cli.py", py_pkg / "cli.py")
    copy_file(upstream_src / "main.py", py_pkg / "_upstream_main.py")
    copy_file(upstream_src / "point.py", py_pkg / "_upstream_point.py")

    # Upstream tests and fixtures (run from this repo root).
    tests_upstream = ROOT / "tests" / "upstream"
    tests_upstream.mkdir(parents=True, exist_ok=True)
    for helper in ["conftest.py", "myfunc.py", "__init__.py"]:
        src = upstream_tests / helper
        if src.exists():
            copy_file(src, tests_upstream / helper)

    for test_file in sorted(upstream_tests.glob("test_*.py")):
        copy_file(test_file, tests_upstream / test_file.name)

    copy_tree(upstream_tests / "data", ROOT / "tests" / "data")
    copy_tree(upstream_tests / "data", ROOT / "tests" / "upstream" / "data")

    # Stamp pinned commit.
    (vendor_dir / "SHA.txt").write_text(f"{args.sha}\n", encoding="utf-8")

    manifest = {
        "repo": str(repo),
        "sha": args.sha,
        "copied_source_files": copied_src,
        "copied_test_files": copied_tests,
    }
    (vendor_dir / "sync_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
