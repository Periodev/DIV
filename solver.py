# solver.py - CLI entry point for BFS level solver
#
# Usage:
#   python solver.py <level_id> [max_depth]
#   python solver.py 0-1
#   python solver.py 1-3 80

import sys
import time
from level_constructor import MAIN_LEVELS
from solver_core import solve


def find_level(level_id: str) -> dict:
    for level in MAIN_LEVELS:
        if level['id'] == level_id:
            return level
    return None


def progress(states, visited):
    print(f"  ... {states} states explored, {visited} unique", flush=True)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python solver.py <level_id> [max_depth]")
        print("Example: python solver.py 0-1")
        sys.exit(1)

    level_id = sys.argv[1]
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 80

    level = find_level(level_id)
    if not level:
        print(f"Level '{level_id}' not found.")
        print(f"Available: {[lv['id'] for lv in MAIN_LEVELS]}")
        sys.exit(1)

    print(f"Solving {level['id']} {level['name']}  (max depth {max_depth})")
    t0 = time.time()
    result = solve(level, max_depth=max_depth, progress_cb=progress)
    elapsed = time.time() - t0

    if result:
        print(f"Solution ({len(result)} steps) in {elapsed:.2f}s: {result}")
    else:
        print(f"No solution found within depth {max_depth} ({elapsed:.2f}s)")
