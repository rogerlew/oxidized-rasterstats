#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import inspect
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate public API surface manifest")
    parser.add_argument("--output", type=Path, default=Path("tests/compat/api_manifest.json"))
    args = parser.parse_args()

    module = importlib.import_module("rasterstats")
    exports = list(getattr(module, "__all__", []))

    signatures: dict[str, str] = {}
    for name in exports:
        obj = getattr(module, name, None)
        if callable(obj):
            try:
                signatures[name] = str(inspect.signature(obj))
            except (TypeError, ValueError):
                signatures[name] = "<unavailable>"

    payload = {
        "module": "rasterstats",
        "exports": exports,
        "signatures": signatures,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
