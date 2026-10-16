#!/usr/bin/env python3
"""Export one reviewed item collection to deterministic learning ecosystems."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from praxexports import (
    ExportError,
    export_artifact,
    load_collection,
    sha256_bytes,
    validate_artifact,
)
from praxexports.core import DEFAULT_EPOCH, FORMATS, MODEL_VERSION, atomic_write


def receipt(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"


def parse_epoch(value: str) -> int:
    try:
        epoch = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "epoch must be an integer Unix timestamp"
        ) from exc
    if str(epoch) != value.strip() and value.strip() not in {
        f"+{epoch}",
        f"-{abs(epoch)}",
    }:
        raise argparse.ArgumentTypeError(
            "epoch must be a base-10 integer without a decimal point"
        )
    return epoch


def default_epoch() -> int:
    raw = os.environ.get("SOURCE_DATE_EPOCH")
    if raw is None:
        return DEFAULT_EPOCH
    try:
        return parse_epoch(raw)
    except argparse.ArgumentTypeError as exc:
        raise ExportError(f"invalid SOURCE_DATE_EPOCH: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministically export and validate Prax Teach learning items."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser(
        "export", help="export a reviewed JSON item collection"
    )
    export.add_argument("format", choices=FORMATS)
    export.add_argument("source", type=Path)
    export.add_argument("output", type=Path)
    export.add_argument(
        "--epoch", type=parse_epoch, help="UTC build-date epoch for ZIP metadata"
    )

    validate = subparsers.add_parser(
        "validate", help="validate a generated ecosystem artifact"
    )
    validate.add_argument("format", choices=FORMATS)
    validate.add_argument("artifact", type=Path)
    return parser


def run_export(args: argparse.Namespace) -> int:
    try:
        if args.source.resolve(strict=False) == args.output.resolve(strict=False):
            raise ExportError("source and output paths must differ")
        collection = load_collection(args.source)
        epoch = default_epoch() if args.epoch is None else args.epoch
        data, details = export_artifact(args.format, collection, epoch)
        atomic_write(args.output, data)
        result = {
            "command": "export",
            "valid": True,
            "format": args.format,
            "model_version": MODEL_VERSION,
            "source": str(args.source),
            "output": str(args.output),
            "sha256": sha256_bytes(data),
            "size_bytes": len(data),
            "epoch": epoch,
            "details": details,
        }
    except ExportError as exc:
        print(
            receipt(
                {
                    "command": "export",
                    "valid": False,
                    "format": args.format,
                    "error": str(exc),
                }
            ),
            end="",
            file=sys.stderr,
        )
        return 2
    print(receipt(result), end="")
    return 0


def run_validate(args: argparse.Namespace) -> int:
    try:
        data, details = validate_artifact(args.format, args.artifact)
        result = {
            "command": "validate",
            "valid": True,
            "format": args.format,
            "artifact": str(args.artifact),
            "sha256": sha256_bytes(data),
            "size_bytes": len(data),
            "details": details,
        }
        print(receipt(result), end="")
        return 0
    except ExportError as exc:
        print(
            receipt(
                {
                    "command": "validate",
                    "valid": False,
                    "format": args.format,
                    "artifact": str(args.artifact),
                    "error": str(exc),
                }
            ),
            end="",
        )
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "export":
        return run_export(args)
    return run_validate(args)


if __name__ == "__main__":
    raise SystemExit(main())
