"""Structurally compare two trace JSON files produced by trace_runner.py / TraceRunner.gd.

Usage:
    python tools/diff_trace.py <py_trace.json> <gd_trace.json>

Exits 0 if identical, 1 if any difference found.
Prints the first diverging step and the specific fields that differ.
"""

import json
import sys


def find_diff(a, b, path: str, out: list) -> None:
    if type(a) != type(b):
        out.append(f"  TYPE {path}: {type(a).__name__} vs {type(b).__name__}")
        return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            find_diff(a.get(k), b.get(k), f"{path}.{k}", out)
    elif isinstance(a, list):
        for j in range(max(len(a), len(b))):
            av = a[j] if j < len(a) else "<missing>"
            bv = b[j] if j < len(b) else "<missing>"
            find_diff(av, bv, f"{path}[{j}]", out)
    else:
        if a != b:
            out.append(f"  {path}:\n    py = {a!r}\n    gd = {b!r}")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2

    py_trace = json.load(open(sys.argv[1], encoding="utf-8"))
    gd_trace = json.load(open(sys.argv[2], encoding="utf-8"))

    print(f"Steps: py={len(py_trace)}  gd={len(gd_trace)}")

    for i, (ps, gs) in enumerate(zip(py_trace, gd_trace)):
        if ps == gs:
            continue
        out: list = []
        find_diff(ps, gs, f"step[{i}] move={ps['move']!r}", out)
        if out:
            print(f"\nFirst divergence at step {i} (move={ps['move']!r}):")
            for line in out[:40]:
                print(line)
            return 1

    if len(py_trace) != len(gd_trace):
        n = min(len(py_trace), len(gd_trace))
        print(f"\nContent matches up to step {n-1}, but step counts differ.")
        return 1

    print("IDENTICAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
