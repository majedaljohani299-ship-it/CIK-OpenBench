"""Run unittest suites and fail closed when zero tests are discovered."""
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

# Direct execution from tools/ otherwise hides the project root from Python imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-dir", default="tests", help="Directory for unittest discovery")
    args = parser.parse_args(argv)
    try:
        suite = unittest.defaultTestLoader.discover(args.start_dir, pattern="test_*.py")
    except (ImportError, OSError) as exc:
        print(f"TEST_DISCOVERY_ERROR: {exc}", file=sys.stderr)
        return 2
    count = suite.countTestCases()
    if count == 0:
        print("FAIL_ZERO_TESTS: no tests discovered; never mark CI as PASS", file=sys.stderr)
        return 2
    print(f"DISCOVERED {count} tests (must be > 0)", flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
