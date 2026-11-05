#!/usr/bin/env python3
"""Generate a Python-first Raceboat encoding plugin with unimplemented codec hooks."""

import argparse
import json
import math
import re
import shutil
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if not 0 < parsed <= 2**31 - 1:
        raise argparse.ArgumentTypeError("must be a positive int32")
    return parsed


def positive_seconds(value):
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a number of seconds") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be finite positive seconds")
    return parsed


def mime_type(value):
    if not re.fullmatch(r"[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+", value):
        raise argparse.ArgumentTypeError("must be a concrete MIME type")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="CamelCase codec name")
    parser.add_argument("--mime-type", required=True, type=mime_type)
    parser.add_argument("--max-bytes", required=True, type=positive_int)
    parser.add_argument("--encoding-time-seconds", required=True, type=positive_seconds)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", args.name):
        parser.error("--name must be CamelCase, e.g. MyCodec")
    output = args.out.resolve()
    if output.exists():
        parser.error("--out must not already exist")
    if TEMPLATE == output or TEMPLATE in output.parents:
        parser.error("--out must be outside the template")
    encoding_id = args.name[0].lower() + args.name[1:]
    package = "Plugin" + args.name + "Encoding"
    for source in sorted(TEMPLATE.rglob("*")):
        relative = source.relative_to(TEMPLATE)
        if (set(relative.parts) & {".git", "__pycache__", "build", "kit", ".venv"}
                or not source.is_file()
                or source.name in {"new_encoding.py", "test_generator.py", "test_stub_codec.py"}):
            continue
        destination = output / str(relative).replace("PluginPythonStubEncoding", package)
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text().replace("PluginPythonStubEncoding", package)
        text = text.replace("pythonStub", encoding_id)
        destination.write_text(text)
        shutil.copymode(source, destination)
    metadata = {
        "encoding_id": encoding_id,
        "mime_type": args.mime_type,
        "max_bytes": args.max_bytes,
        "encoding_time_seconds": args.encoding_time_seconds,
    }
    (output / "source" / package / "metadata.json").write_text(json.dumps(metadata, indent=4) + "\n")
    print("Created {} (encoding id: {})".format(output, encoding_id))
    print("Implement codec.py, pin dependencies, and verify capacity/timing before integration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())