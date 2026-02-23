#!/usr/bin/env python3
"""Stress trace parity runner across all levels.

Runs move sequences on both Python and Godot trace runners, then diffs their
JSON traces. Intended for timeline-system regression checks.

Modes:
  --solutions   Use solver solutions from solver_solutions_skip_0-8.txt.
                Every step is a valid game action (V/C/T/X included).
                This is the recommended mode — best logic coverage.

  --random      Use random sequences (default when --solutions is absent).
                Most moves will be NOOPs (hitting walls, invalid V/C/T).
                Useful only as a sanity check that NOOPs match too.

Examples:
    py -3 tools/stress_trace_all_levels.py --solutions
    py -3 tools/stress_trace_all_levels.py --runs 3 --length 40
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from diff_trace import find_diff
from level_constructor import load_main_levels
from trace_runner import run_trace


ALPHABET = "UDLRVCFTXPOZ"
DEFAULT_GODOT = "D:/Godot/Godot_4.5.1/Godot_v4.5.1-stable_win64_console.exe"
SOLUTIONS_FILE = Path(__file__).resolve().parent / "solver_solutions_skip_0-8.txt"


def make_sequence(seed: int, length: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice(ALPHABET) for _ in range(length))


def load_solutions() -> Dict[str, str]:
    """Parse solver_solutions_skip_0-8.txt → {level_id: moves_string}."""
    solutions: Dict[str, str] = {}
    if not SOLUTIONS_FILE.exists():
        return solutions
    for line in SOLUTIONS_FILE.read_text(encoding="utf-8").splitlines():
        # Format: " 0-1 | PASS | steps=11 | t=  0.00s | depth=80 | UUURRRRRDDD"
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6 and parts[1] == "PASS":
            level_id = parts[0]
            moves = parts[5]
            solutions[level_id] = moves
    return solutions


def run_godot_trace(godot_exe: str, level_idx: int, seq: str) -> List[Dict[str, Any]]:
    cmd = [
        godot_exe,
        "--headless",
        "--script",
        "res://scripts/TraceRunner.gd",
        "--path",
        "godot",
        "--",
        str(level_idx),
        seq,
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        raise RuntimeError(
            "Godot trace runner failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"Exit: {proc.returncode}\n"
            f"STDERR:\n{stderr}\n"
            f"STDOUT:\n{stdout}"
        )

    # Godot may print banner/log lines before JSON. Keep JSON payload only.
    start = proc.stdout.find("[")
    end = proc.stdout.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise RuntimeError(
            "Could not locate JSON array in Godot output.\n"
            f"Raw STDOUT:\n{proc.stdout}"
        )
    payload = proc.stdout[start : end + 1]
    return json.loads(payload)


def compare_traces(py_trace: List[Dict[str, Any]], gd_trace: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    if py_trace == gd_trace:
        return True, []

    # Match diff_trace.py behavior: first divergent step, then field-level diffs.
    for i, (ps, gs) in enumerate(zip(py_trace, gd_trace)):
        if ps == gs:
            continue
        out: List[str] = []
        move = ps.get("move", "?")
        find_diff(ps, gs, f"step[{i}] move={move!r}", out)
        return False, out[:80]

    if len(py_trace) != len(gd_trace):
        return False, [f"Step count mismatch: py={len(py_trace)} gd={len(gd_trace)}"]

    return False, ["Unknown mismatch (content differs but no diff details found)."]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run trace parity checks (Python vs GDScript) for all levels.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--solutions",
        action="store_true",
        help="Use solver solutions (recommended — all steps are valid game actions)",
    )
    mode.add_argument(
        "--random",
        action="store_true",
        help="Use random sequences (default when neither flag is given)",
    )
    p.add_argument("--runs", type=int, default=3, help="Random sequences per level (default: 3)")
    p.add_argument("--length", type=int, default=40, help="Moves per random sequence (default: 40)")
    p.add_argument("--seed", type=int, default=20260224, help="Base seed (default: 20260224)")
    p.add_argument("--start-level", type=int, default=0, help="Start level index (default: 0)")
    p.add_argument("--end-level", type=int, default=-1, help="End level index inclusive (-1 = last)")
    p.add_argument("--godot-exe", default=DEFAULT_GODOT, help="Godot console executable path")
    p.add_argument(
        "--outdir",
        default="tmp/stress_trace",
        help="Output directory for generated sequences/traces (default: tmp/stress_trace)",
    )
    p.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first mismatch/error (default: continue and summarize all)",
    )
    return p.parse_args()


def _run_one(
    args: argparse.Namespace,
    levels: List[Dict[str, Any]],
    level_idx: int,
    seq: str,
    label: str,
    outdir: Path,
    failures: List[Tuple[int, str, str, str]],
) -> bool:
    """Run a single (level_idx, seq) case. Returns True on pass."""
    level = levels[level_idx]
    level_id = str(level.get("id", level_idx))
    level_slug = level_id.replace("/", "_").replace("-", "_")
    slug_label = label.replace(" ", "_").replace("=", "")

    base = f"lvl_{level_idx:03d}_{level_slug}_{slug_label}"
    seq_path = outdir / f"{base}.seq.txt"
    py_path  = outdir / f"{base}.py.json"
    gd_path  = outdir / f"{base}.gd.json"
    diff_path = outdir / f"{base}.diff.txt"

    seq_path.write_text(seq + "\n", encoding="utf-8")

    try:
        py_trace = run_trace(level, seq)
        py_path.write_text(
            json.dumps(py_trace, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        gd_trace = run_godot_trace(args.godot_exe, level_idx, seq)
        gd_path.write_text(
            json.dumps(gd_trace, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        ok, diff_lines = compare_traces(py_trace, gd_trace)
        if ok:
            print(f"[OK]   level={level_idx:2d} ({level_id:>4}) {label}  moves={len(seq)}")
            return True

        diff_path.write_text("\n".join(diff_lines) + "\n", encoding="utf-8")
        failures.append((level_idx, label, level_id, str(diff_path)))
        print(f"[FAIL] level={level_idx:2d} ({level_id:>4}) {label} -> {diff_path}")
        return False

    except Exception as exc:  # noqa: BLE001
        msg = f"ERROR: {exc}"
        diff_path.write_text(msg + "\n", encoding="utf-8")
        failures.append((level_idx, label, level_id, str(diff_path)))
        print(f"[ERR]  level={level_idx:2d} ({level_id:>4}) {label} -> {msg[:120]}")
        return False


def main() -> int:
    args = parse_args()
    use_solutions = args.solutions  # --random or neither → random mode

    levels = load_main_levels()
    if not levels:
        print("No levels found from level_constructor.load_main_levels().", file=sys.stderr)
        return 2

    start = max(0, args.start_level)
    end = (len(levels) - 1) if args.end_level < 0 else min(args.end_level, len(levels) - 1)
    if start > end:
        print(f"Invalid level range: start={start}, end={end}", file=sys.stderr)
        return 2

    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    solutions: Dict[str, str] = {}
    if use_solutions:
        solutions = load_solutions()
        if not solutions:
            print(
                f"No solutions found in {SOLUTIONS_FILE}. "
                "Run the solver first or use --random mode.",
                file=sys.stderr,
            )
            return 2
        mode_desc = f"solutions ({len(solutions)} available)"
    else:
        mode_desc = f"random runs={args.runs} length={args.length} seed={args.seed}"

    print(f"Parity check: levels {start}..{end}, mode={mode_desc}")
    print(f"Godot exe: {args.godot_exe}")
    print(f"Output dir: {outdir}")

    total_cases = 0
    failed_cases = 0
    failures: List[Tuple[int, str, str, str]] = []

    for level_idx in range(start, end + 1):
        level = levels[level_idx]
        level_id = str(level.get("id", level_idx))

        if use_solutions:
            seq = solutions.get(level_id)
            if seq is None:
                print(f"[SKIP] level={level_idx} ({level_id}) — no solution found")
                continue
            total_cases += 1
            ok = _run_one(args, levels, level_idx, seq, "solution", outdir, failures)
            if not ok:
                failed_cases += 1
                if args.fail_fast:
                    print("Fail-fast enabled, stopping.")
                    break
        else:
            for run_idx in range(1, args.runs + 1):
                total_cases += 1
                seq_seed = args.seed + level_idx * 1000 + run_idx
                seq = make_sequence(seq_seed, args.length)
                label = f"run{run_idx:02d}_seed{seq_seed}"
                ok = _run_one(args, levels, level_idx, seq, label, outdir, failures)
                if not ok:
                    failed_cases += 1
                    if args.fail_fast:
                        print("Fail-fast enabled, stopping.")
                        break
            if failed_cases and args.fail_fast:
                break

    passed = total_cases - failed_cases
    print(f"\nSummary: {total_cases} cases, {passed} passed, {failed_cases} failed")

    if failures:
        print("\nFailures:")
        for level_idx, label, level_id, path in failures:
            print(f"  level={level_idx} ({level_id}) {label} -> {path}")
        return 1

    print("All traces IDENTICAL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

