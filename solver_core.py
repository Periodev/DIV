# solver_core.py - BFS level solver (pure logic, no Arcade dependency)

import copy
from collections import deque
from map_parser import parse_dual_layer
from game_controller import GameController
from game_logic import GameLogic
from replay_core import execute_action, DIRECTION_MAP

_OPPOSITES = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}


def _state_key(c: GameController) -> tuple:
    """Hashable snapshot of controller state (terrain is fixed, excluded)."""
    def branch_key(b):
        if b is None:
            return None
        entities = frozenset(
            (e.uid, e.pos, e.z, e.type.value, e.holder,
             frozenset(e.fused_from) if e.fused_from else None,
             b.is_shadow(e.uid))
            for e in b.entities
        )
        return (b.player.pos, b.player.direction, entities)

    return (
        branch_key(c.main_branch),
        branch_key(c.sub_branch),
        c.current_focus,
        c.has_branched,
    )


def _is_noop(ctrl: GameController, action: str, last_action: str = None) -> bool:
    """Pre-check: is this action definitely a no-op? Avoids unnecessary deepcopy."""

    # Pattern: T→T (switch focus then immediately switch back)
    if action == 'T' and last_action == 'T':
        return True

    # Pattern: V→C/I (branch then immediately merge)
    if action in ('C', 'I') and last_action == 'V':
        return True

    if action in DIRECTION_MAP:
        direction = DIRECTION_MAP[action]
        active = ctrl.get_active_branch()
        px, py = active.player.pos
        dx, dy = direction
        target_pos = (px + dx, py + dy)
        is_holding = bool(active.get_held_items())
        has_box_ahead = active.has_box_at(target_pos)

        # Reverse movement in open area: would revisit a previously visited state.
        # Safe to skip when the last move was pure movement (no box pushed).
        # Detect push: if a box now sits in the direction we just came from, last move was a push.
        if not is_holding and last_action in _OPPOSITES and action == _OPPOSITES[last_action]:
            fwd = DIRECTION_MAP[last_action]
            pushed_pos = (px + fwd[0], py + fwd[1])
            if not active.has_box_at(pushed_pos):
                return True

        if is_holding or has_box_ahead:
            # Two-step turning: first press turns (valid action), second press moves
            if active.player.direction != direction:
                return False  # Turn is a valid action
            return not GameLogic.can_move(active, direction)
        else:
            # Open area: move immediately (direction set as side effect, not logged)
            return not GameLogic.can_move(active, direction)

    elif action == 'V':
        if ctrl.has_branched:
            return True
        # Also skip if player is not standing on a branch point
        active = ctrl.get_active_branch()
        terrain = active.terrain.get(active.player.pos)
        return terrain not in GameController.BRANCH_DECREMENT

    elif action in ('C', 'I', 'T'):
        return not ctrl.has_branched  # can't merge/switch if not branched

    return False  # X, P, O: complex conditions, allow deepcopy


def _actions_for(hints: dict) -> list:
    """Build candidate action list from level hints."""
    actions = ['U', 'D', 'L', 'R']
    if hints.get('diverge'):
        actions.append('V')
    actions += ['C', 'T']  # merge / switch focus: controller guards has_branched
    if hints.get('inherit'):
        actions.append('I')
    if hints.get('converge') or hints.get('pickup'):
        actions.append('X')
    if hints.get('pickup'):
        actions += ['P', 'O']
    return actions


def solve(level_dict: dict, max_depth: int = 60,
          progress_cb=None) -> str | None:
    """BFS solver. Returns solution string or None if not found.

    Args:
        level_dict:   level data dict (floor_map, object_map, hints)
        max_depth:    maximum sequence length to search
        progress_cb:  optional callable(states_visited) for progress reporting
    """
    hints = level_dict.get('hints') or {
        'diverge': True, 'converge': True, 'pickup': True, 'inherit': True,
    }
    source = parse_dual_layer(level_dict['floor_map'], level_dict['object_map'])
    actions = _actions_for(hints)

    initial = GameController(source)
    queue = deque([(initial, '')])
    visited = {_state_key(initial)}
    count = 0

    while queue:
        ctrl, path = queue.popleft()
        count += 1
        if progress_cb and count % 5000 == 0:
            progress_cb(count, len(visited))

        if len(path) >= max_depth:
            continue

        last_action = path[-1] if path else None
        for action in actions:
            if _is_noop(ctrl, action, last_action):
                continue
            new_ctrl = copy.deepcopy(ctrl)
            execute_action(new_ctrl, action, hints)

            if not new_ctrl.collapsed and not new_ctrl.victory:
                new_ctrl.update_physics()
            if not new_ctrl.victory:
                new_ctrl.check_victory()

            if new_ctrl.collapsed:
                continue

            new_path = path + action

            if new_ctrl.victory:
                return new_path

            new_key = _state_key(new_ctrl)
            if new_key not in visited:
                visited.add(new_key)
                queue.append((new_ctrl, new_path))

    return None
