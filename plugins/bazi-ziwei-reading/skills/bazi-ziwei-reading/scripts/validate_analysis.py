#!/usr/bin/env python3
"""Validate analysis.json against the deterministic chart.json facts."""

import argparse
import json
import sys

from analysis_schema import validate_analysis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart", required=True)
    parser.add_argument("--analysis", required=True)
    args = parser.parse_args()

    with open(args.chart, encoding="utf-8-sig") as handle:
        chart = json.load(handle)
    with open(args.analysis, encoding="utf-8-sig") as handle:
        analysis = json.load(handle)

    errors = validate_analysis(chart, analysis)
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        print(f"{len(errors)} validation error(s)", file=sys.stderr)
        return 1
    print("PASS analysis schema and chart references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
