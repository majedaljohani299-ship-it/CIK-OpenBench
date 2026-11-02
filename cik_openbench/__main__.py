"""CIK OpenBench command line interface; uses Python standard library only."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import BenchError, evaluate, prepare, read_json, write_new_json, write_private_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline, blinded paired-evaluation harness; no claims of model improvement")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare", help="Create blinded packet and private mapping key")
    p.add_argument("--input", required=True)
    p.add_argument("--packet", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--seed", type=int, default=None, help="For replayable examples; keep key private for real blind evaluations")
    s = commands.add_parser("score", help="Score manually judged A/B pairs against private mapping")
    s.add_argument("--packet", required=True)
    s.add_argument("--key", required=True)
    s.add_argument("--judgments", required=True)
    s.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            inputs = [Path(p).resolve() for p in (args.input, args.packet, args.key)]
            if len(set(inputs)) != 3:
                raise BenchError("Input, blinded packet, and private key must have different paths")
            if Path(args.packet).exists() or Path(args.key).exists():
                raise BenchError("Use new output paths; refusing to overwrite an existing packet or private key")
            packet, key = prepare(read_json(args.input), seed=args.seed)
            write_private_json(args.key, key)
            try:
                write_new_json(args.packet, packet)
            except BaseException:
                Path(args.key).unlink(missing_ok=True)
                raise
            print(f"PREPARED {len(packet['pairs'])} synthetic/research pairs. Do not publish the private key.")
            return 0
        source_paths = {Path(p).resolve() for p in (args.packet, args.key, args.judgments)}
        if Path(args.report).resolve() in source_paths:
            raise BenchError("Report output path must differ from all input paths")
        report = evaluate(read_json(args.packet), read_json(args.key), read_json(args.judgments))
        write_new_json(args.report, report)
        print(f"{report['status']}: {report['judged_pairs']}/{report['total_pairs']} judged pairs")
        return 0 if report["status"] == "EVALUATED_NO_EFFICACY_CLAIM" else 2
    except BenchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
