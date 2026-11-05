#!/usr/bin/env python3
"""Stage a source-only encoding kit; this does not certify the codec."""

import argparse
import json
import platform
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=("x86_64", "arm64-v8a"),
                        default={"aarch64": "arm64-v8a"}.get(platform.machine(), platform.machine()))
    args = parser.parse_args()
    if args.arch not in ("x86_64", "arm64-v8a"):
        parser.error("unsupported architecture; specify --arch")
    source = ROOT / "source"
    manifest = json.loads((source / "manifest.json").read_text())
    entry = manifest["plugins"][0]
    package = entry["file_path"]
    metadata = json.loads((source / package / "metadata.json").read_text())
    if any(value is None for value in metadata.values()):
        parser.error("template metadata is unset; generate a plugin with new_encoding.py first")
    for role in ("client", "server"):
        destination = ROOT / "kit" / "artifacts" / ("linux-" + args.arch + "-" + role) / package
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source / package, destination,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(source / "manifest.json", destination / "manifest.json")
        shutil.copy2(ROOT / "requirements.txt", destination / "requirements.txt")
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())