#!/usr/bin/env python3
"""CRAP score per function: complexity^2 * (1 - coverage)^3 + complexity.

Complexity comes from lizard (Python, TypeScript and Vue alike), coverage from an
lcov report (pytest-cov and vitest both write one), so a single script serves
every service.

    crap.py --src backend/app --lcov backend/coverage.lcov --root backend --name backend

Prints a table of the worst functions, appends it to the GitHub job summary when
there is one, and exits 1 if a function is over --threshold and --fail is set.
"""

import argparse
import csv
import io
import os
import subprocess
import sys
from pathlib import Path


def parse_lcov(path: Path, root: Path) -> dict[str, dict[int, int]]:
    """Map each source file (absolute path) to {line: hit count}."""
    files: dict[str, dict[int, int]] = {}
    current: dict[int, int] | None = None
    for raw in path.read_text().splitlines():
        if raw.startswith("SF:"):
            source = Path(raw[3:])
            current = files.setdefault(str((source if source.is_absolute() else root / source).resolve()), {})
        elif raw.startswith("DA:") and current is not None:
            line, hits, *_ = raw[3:].split(",")
            current[int(line)] = int(hits)
    return files


def complexity(src: Path) -> list[dict]:
    """Run lizard over `src` and return one row per function."""
    out = subprocess.run(
        ["lizard", "--csv", str(src)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    fields = ["nloc", "ccn", "tokens", "params", "length", "location", "file", "name", "long_name", "start", "end"]
    rows = (dict(zip(fields, row)) for row in csv.reader(io.StringIO(out)))
    return [
        r
        for r in rows
        if r["file"].endswith((".py", ".ts", ".vue"))
        # What only the tests use (the fake backend of the pages' tests, in a `test` directory) is not the code to judge.
        and not r["file"].endswith((".test.ts", ".spec.ts"))
        and "/test/" not in r["file"]
    ]


def crap(ccn: int, cov: float) -> float:
    return ccn**2 * (1 - cov) ** 3 + ccn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path, help="source directory to analyse")
    ap.add_argument("--lcov", required=True, type=Path, help="lcov coverage report")
    ap.add_argument("--name", required=True, help="label used in the report")
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="directory the lcov paths are relative to")
    ap.add_argument("--threshold", type=float, default=float(os.environ.get("CRAP_THRESHOLD", 30)))
    ap.add_argument("--fail", action="store_true", help="exit 1 when a function is over the threshold")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    coverage = parse_lcov(args.lcov, args.root.resolve())
    rows = []
    for fn in complexity(args.src):
        lines = coverage.get(str(Path(fn["file"]).resolve()))
        start, end, ccn = int(fn["start"]), int(fn["end"]), int(fn["ccn"])
        if lines is None:
            cov = 0.0  # file never imported by the tests
        else:
            hits = [h for n, h in lines.items() if start <= n <= end]
            cov = sum(h > 0 for h in hits) / len(hits) if hits else 1.0
        rows.append((crap(ccn, cov), ccn, cov, fn["file"], fn["name"], start))

    rows.sort(reverse=True)
    over = [r for r in rows if r[0] > args.threshold]
    lines_out = [
        f"### CRAP score - {args.name}",
        "",
        f"{len(rows)} functions, {len(over)} over the threshold of {args.threshold:g}.",
        "",
        "| CRAP | Complexity | Coverage | Function |",
        "|-----:|-----------:|---------:|----------|",
    ]
    for score, ccn, cov, file, name, start in rows[: args.top]:
        lines_out.append(f"| {score:.1f} | {ccn} | {cov:.0%} | `{file}:{start}` {name} |")
    report = "\n".join(lines_out)

    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as f:
            f.write(report + "\n")

    if over and args.fail:
        print(f"::error::{len(over)} function(s) over the CRAP threshold of {args.threshold:g}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
