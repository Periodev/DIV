import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from solver_core import solve

level = {
    'id': 'Extract',
    'name': 'Extract 抽取',
    'floor_map': '###HG\n#S.H#\n#H#S#\n..Hv#\nv.###',
    'object_map': '.....\n..B..\n...B.\n.B...\nP....',
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
