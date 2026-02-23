"""Serialize BranchState and run move traces for cross-implementation comparison.

Usage:
    python tools/trace_runner.py <level_id_or_index> [moves]
    python tools/trace_runner.py 0-1 UUDDRPVTCF > trace.json
    python tools/trace_runner.py 2  ""  # dump initial state of level index 2

Output: JSON array, one entry per step:
    [{"step": 0, "move": "", "state": {...}}, {"step": 1, "move": "U", ...}, ...]

The 'state' schema is canonical (terrain sorted, entities sorted by uid) so
the GDScript equivalent can produce identical JSON and both can be diffed directly.
"""

import json
import os
import sys

# Make root and tools importable regardless of working directory.
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.join(_TOOLS_DIR, '..')
for _p in (_TOOLS_DIR, _ROOT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from timeline_system import BranchState, Entity, TerrainType, EntityType
from game_controller import GameController
from replay_core import Replayer


# ---------------------------------------------------------------------------
# Enum → int (must match Enums.gd exactly)
# ---------------------------------------------------------------------------

TERRAIN_INT: dict = {
    TerrainType.FLOOR:    0,
    TerrainType.WALL:     1,
    TerrainType.SWITCH:   2,
    TerrainType.NO_CARRY: 3,
    TerrainType.BRANCH1:  4,
    TerrainType.BRANCH2:  5,
    TerrainType.BRANCH3:  6,
    TerrainType.BRANCH4:  7,
    TerrainType.GOAL:     8,
    TerrainType.HOLE:     9,
}

ENTITY_TYPE_INT: dict = {
    EntityType.PLAYER: 0,
    EntityType.BOX:    1,
}


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def serialize_branch_state(branch: BranchState) -> dict:
    """Canonical JSON-serialisable dict for one BranchState.

    Canonical rules (GDScript must follow the same):
    - terrain keys sorted by (x, y), encoded as "x,y" string
    - terrain values as int (matching Enums.TerrainType)
    - entities sorted by uid
    - holder=None  → -1
    - fused_from=None/frozenset → sorted int list ([] if empty)
    - direction as [dx, dy]
    """
    terrain = {
        f"{pos[0]},{pos[1]}": TERRAIN_INT[t]
        for pos, t in sorted(branch.terrain.items())
    }
    entities = [
        {
            "uid":        e.uid,
            "type":       ENTITY_TYPE_INT[e.type],
            "pos":        [e.pos[0], e.pos[1]],
            "z":          e.z,
            "holder":     -1 if e.holder is None else e.holder,
            "collision":  e.collision,
            "weight":     e.weight,
            "direction":  [e.direction[0], e.direction[1]],
            "fused_from": sorted(e.fused_from) if e.fused_from else [],
        }
        for e in sorted(branch.entities, key=lambda e: e.uid)
    ]
    return {
        "grid_size": branch.grid_size,
        "next_uid":  branch.next_uid,
        "terrain":   terrain,
        "entities":  entities,
    }


def serialize_controller_state(ctrl: GameController) -> dict:
    """Full controller state snapshot (both branches + meta flags)."""
    return {
        "has_branched":  ctrl.has_branched,
        "current_focus": ctrl.current_focus,
        "collapsed":     ctrl.collapsed,
        "victory":       ctrl.victory,
        "main_branch":   serialize_branch_state(ctrl.main_branch),
        "sub_branch":    serialize_branch_state(ctrl.sub_branch) if ctrl.sub_branch else None,
    }


# ---------------------------------------------------------------------------
# Trace runner
# ---------------------------------------------------------------------------

def run_trace(level_dict: dict, moves: str) -> list:
    """Execute a move sequence and capture full controller state after each step.

    Physics is settled after every action (delegates to Replayer._execute).

    Returns:
        list of {"step": int, "move": str, "state": dict}
        step 0 = initial state (after physics settle, before any move)
    """
    replayer = Replayer(level_dict)
    replayer.load(moves)   # seek(0): reset + settle initial physics

    trace = [{
        "step": 0,
        "move": "",
        "state": serialize_controller_state(replayer.controller),
    }]

    for _ in moves:
        replayer.step_forward()
        step = replayer.position          # 1-based index after step_forward
        trace.append({
            "step": step,
            "move": moves[step - 1],
            "state": serialize_controller_state(replayer.controller),
        })

    return trace


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_level(id_or_idx: str) -> dict:
    from level_constructor import load_main_levels
    levels = load_main_levels()
    if not levels:
        raise SystemExit("No levels found — check Level/ directory")
    if id_or_idx.isdigit():
        idx = int(id_or_idx)
        if not 0 <= idx < len(levels):
            raise SystemExit(f"Index {idx} out of range (0–{len(levels)-1})")
        return levels[idx]
    for lv in levels:
        if lv["id"] == id_or_idx:
            return lv
    raise SystemExit(
        f"Level '{id_or_idx}' not found. "
        f"Available: {[lv['id'] for lv in levels[:8]]}..."
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    level  = _load_level(sys.argv[1])
    moves  = sys.argv[2] if len(sys.argv) > 2 else ""
    trace  = run_trace(level, moves)
    print(json.dumps(trace, indent=2, ensure_ascii=False))
