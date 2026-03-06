# solver.py - CLI entry point for BFS / fast solver
#
# Usage:
#   python solver.py <level_id> [max_depth] [--bfs|--fast]
#   python solver.py 0-1
#   python solver.py 1-3 80
#   python solver.py 3-9 80 --fast

import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import time
from level_constructor import MAIN_LEVELS
from solver_core import solve, solve_fast


def find_level(level_id: str) -> dict:
    for level in MAIN_LEVELS:
        if level['id'] == level_id:
            return level
    return None


def progress(states, visited):
    print(f"  ... {states} states explored, {visited} unique", flush=True)


def parse_args(argv: list[str]) -> tuple[str, int, str, dict]:
    if not argv:
        raise ValueError

    level_id = argv[0]
    max_depth = 80
    mode = 'bfs'
    hint_overrides = {}

    for arg in argv[1:]:
        if arg == '--bfs':
            mode = 'bfs'
        elif arg == '--fast':
            mode = 'fast'
        elif arg == '--no-converge':
            hint_overrides['converge'] = False
        elif arg == '--no-diverge':
            hint_overrides['diverge'] = False
        elif arg == '--no-pickup':
            hint_overrides['pickup'] = False
        else:
            try:
                max_depth = int(arg)
            except ValueError as exc:
                raise ValueError(f"Unknown argument: {arg}") from exc

    return level_id, max_depth, mode, hint_overrides


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python solver.py <level_id> [max_depth] [--bfs|--fast]")
        print("Example: python solver.py 0-1")
        sys.exit(1)

    try:
        level_id, max_depth, mode, hint_overrides = parse_args(sys.argv[1:])
    except ValueError as e:
        print(f"Argument error: {e}")
        print("Usage: python solver.py <level_id> [max_depth] [--bfs|--fast] [--no-converge] [--no-diverge] [--no-pickup]")
        sys.exit(1)

    level = find_level(level_id)
    if not level:
        print(f"Level '{level_id}' not found.")
        print(f"Available: {[lv['id'] for lv in MAIN_LEVELS]}")
        sys.exit(1)

    if hint_overrides:
        level = dict(level)
        level['hints'] = dict(level.get('hints') or {})
        level['hints'].update(hint_overrides)
        overrides_str = ', '.join(f"{k}={v}" for k, v in hint_overrides.items())
        print(f"Hint overrides: {overrides_str}")

    print(f"Solving {level['id']} {level['name']}  (max depth {max_depth}, mode={mode})")
    t0 = time.time()
    if mode == 'fast':
        result = solve_fast(level, max_depth=max_depth, progress_cb=progress)
    else:
        result = solve(level, max_depth=max_depth, progress_cb=progress)
    elapsed = time.time() - t0

    if result:
        print(f"Solution ({len(result)} steps) in {elapsed:.2f}s: {result}")
        print(f"{level['id']} {result}")
    else:
        print(f"No solution found within depth {max_depth} ({elapsed:.2f}s)")
