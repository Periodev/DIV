# bench_macro.py - Compare fast solver against BFS baseline
#
# Runs solve_fast on levels 1-1 through 3-7 (same set as solver_solutions_skip_0-8.txt)
# and prints a side-by-side comparison.
#
# Usage:
#   python bench_macro.py              # all levels 1-1..3-7
#   python bench_macro.py 1-1 1-6 3-9  # specific levels

import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import time

from level_constructor import MAIN_LEVELS
from solver_core import solve, solve_fast

# Baseline from solver_solutions_skip_0-8.txt (primitive-action steps, time in seconds)
BASELINE = {
    '0-1':  (11,    0.00),
    '0-2':  (14,    0.00),
    '0-3':  (19,    0.00),
    '0-4':  (10,    0.02),
    '0-5':  ( 9,    0.01),
    '0-6':  (11,    0.03),
    '0-7':  (13,    0.03),
    '1-1':  ( 9,    0.01),
    '1-2':  (16,    0.09),
    '1-3':  (27,    0.34),
    '1-4':  (18,    0.03),
    '1-5':  (20,    0.05),
    '1-6':  (26,   12.24),
    '2-1':  (14,    0.00),
    '2-2':  (25,    0.06),
    '2-3':  (34,   41.36),
    '2-4':  (20,    1.29),
    '2-5':  (26,    0.89),
    '2-6':  (27,    0.93),
    '2-7':  (32,    2.10),
    '2-8':  (29,    2.02),
    '2-9':  (49,  490.90),
    '2-10': (46,   13.75),
    '2-11': (40,    5.96),
    '3-1':  (24,    0.99),
    '3-2':  (16,    0.61),
    '3-3':  (19,    0.06),
    '3-4':  (20,    0.40),
    '3-5':  (29,   17.42),
    '3-6':  (28,    3.63),
    '3-7':  (50,  878.12),
}

# Default test set (skip 0-8 and 0-9 to match baseline)
DEFAULT_LEVELS = [lid for lid in BASELINE if lid not in ('0-8', '0-9')]


def find_level(level_id):
    for lv in MAIN_LEVELS:
        if lv['id'] == level_id:
            return lv
    return None


def progress(count, states):
    print(f"    ... {count} states explored, {states} unique states", flush=True)


def run_level(level_id, algo='fast', max_depth=80):
    lv = find_level(level_id)
    if lv is None:
        return level_id, None, None, None

    t0 = time.time()
    if algo == 'fast':
        result = solve_fast(lv, max_depth=max_depth, progress_cb=progress)
    else:
        result = solve(lv, max_depth=max_depth, progress_cb=progress)
    elapsed = time.time() - t0
    return level_id, result, len(result) if result else None, elapsed


def main():
    if len(sys.argv) > 1:
        level_ids = sys.argv[1:]
    else:
        level_ids = sorted(DEFAULT_LEVELS,
                           key=lambda x: tuple(int(p) for p in x.split('-')))

    algo = 'fast'
    max_depth = 80

    print(f"Fast solver benchmark  (max_depth={max_depth})")
    print(f"{'Level':>5}  {'BFS steps':>9}  {'BFS t(s)':>8}  "
          f"{'Fast steps':>10}  {'Fast t(s)':>9}  {'Speedup':>7}  Result")
    print("-" * 80)

    total_pass = total_fail = 0
    total_bfs_t = total_fast_t = 0.0

    for lid in level_ids:
        base_steps, base_t = BASELINE.get(lid, (None, None))

        lid_out, result, steps, elapsed = run_level(lid, algo=algo, max_depth=max_depth)

        if result is not None:
            total_pass += 1
            status = 'PASS'
            speedup = f'{base_t / elapsed:.1f}x' if base_t and elapsed > 0.01 else '--'
            total_fast_t += elapsed
            total_bfs_t += base_t or 0
        else:
            total_fail += 1
            status = 'FAIL'
            speedup = '--'
            elapsed = elapsed or 0

        base_steps_str = f'{base_steps:>9}' if base_steps else '         ?'
        base_t_str = f'{base_t:>8.2f}' if base_t is not None else '        ?'
        steps_str = f'{steps:>11}' if steps is not None else '          ?'
        elapsed_str = f'{elapsed:>10.2f}'

        print(f"{lid:>5}  {base_steps_str}  {base_t_str}  "
              f"{steps_str}  {elapsed_str}  {speedup:>7}  {status}")
        if result:
            print(f"        solution: {result}")

    print("-" * 80)
    print(f"PASS: {total_pass}  FAIL: {total_fail}")
    print(f"BFS total: {total_bfs_t:.1f}s   Fast total: {total_fast_t:.1f}s")
    if total_fast_t > 0 and total_bfs_t > 0:
        print(f"Overall speedup: {total_bfs_t / total_fast_t:.1f}x")


if __name__ == '__main__':
    main()
