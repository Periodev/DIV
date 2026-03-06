import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from solver_core import solve

level = {
    'id': 'Redundant',
    'name': 'Redundant 冗餘',
    'floor_map': '##G#\n##v.\n#S.S\n#S.V',
    'object_map': '....\n..P.\n..BB\n....',
    'hints': {'diverge': True, 'pickup': False, 'converge': True, 'fetch': False},
    'objective': {},
}

def progress(states, visited):
    print(f"  ... {states} states explored, {visited} unique", flush=True)

t0 = time.time()
result = solve(level, max_depth=80, progress_cb=progress)
elapsed = time.time() - t0

if result:
    print(f"Solution ({len(result)} steps) in {elapsed:.2f}s: {result}")
    print(f"{level['id']} {result}")
else:
    print(f"No solution found within depth 80 ({elapsed:.2f}s)")
