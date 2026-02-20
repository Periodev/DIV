# solver_core.py - BFS level solver (pure logic, no Arcade dependency)

from collections import deque
from map_parser import parse_dual_layer
from game_controller import GameController
from game_logic import GameLogic
from replay_core import execute_action, DIRECTION_MAP
from timeline_system import Physics, EntityType

_OPPOSITES = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}


def _build_system_action_table() -> dict:
    """Precompute legal system actions (V/C/T/I) by coarse state flags."""
    table = {}
    for has_branched in (False, True):
        for on_branch_point in (False, True):
            for allow_diverge in (False, True):
                for allow_inherit in (False, True):
                    actions = []
                    if not has_branched:
                        if allow_diverge and on_branch_point:
                            actions.append('V')
                    else:
                        actions.extend(['C', 'T'])
                        if allow_inherit:
                            actions.append('I')
                    table[(has_branched, on_branch_point, allow_diverge, allow_inherit)] = tuple(actions)
    return table


_SYSTEM_ACTION_TABLE = _build_system_action_table()


def _canonical_direction(b) -> tuple:
    """Return canonical player direction when orientation is irrelevant."""
    if b is None:
        return (0, 0)

    # Orientation matters while carrying.
    if b.get_held_items():
        return b.player.direction

    # Orientation matters if any adjacent cell has a grounded box.
    px, py = b.player.pos
    for dx, dy in DIRECTION_MAP.values():
        if b.has_box_at((px + dx, py + dy)):
            return b.player.direction

    # No nearby interaction target: orientation is behaviorally irrelevant.
    return (0, 0)


def _branch_key(b) -> tuple | None:
    """Hashable snapshot for one branch."""
    if b is None:
        return None
    entities = frozenset(
        (e.uid, e.pos, e.z, e.type.value, e.holder,
         frozenset(e.fused_from) if e.fused_from else None,
         b.is_shadow(e.uid))
        for e in b.entities
    )
    return (b.player.pos, _canonical_direction(b), entities)


def _state_key(c: GameController) -> tuple:
    """Hashable snapshot of controller state (terrain is fixed, excluded)."""
    main_key = _branch_key(c.main_branch)
    sub_key = _branch_key(c.sub_branch)
    focus_key = c.current_focus

    # Canonicalize branched states so swapping main/sub represents the same state.
    # (main, sub, focus) == (sub, main, 1-focus)
    if c.has_branched and sub_key is not None:
        if main_key > sub_key:
            main_key, sub_key = sub_key, main_key
            focus_key = 1 - focus_key
        elif main_key == sub_key:
            # Perfectly symmetric branches: focus has no distinguishing power.
            focus_key = 0

    return (main_key, sub_key, focus_key, c.has_branched)


def _is_noop(ctrl: GameController, action: str, last_action: str = None,
             hints: dict | None = None) -> bool:
    """Pre-check: is this action definitely a no-op? Avoids unnecessary deepcopy."""
    hints = hints or {}
    allow_converge = hints.get('converge', True)
    allow_pickup = hints.get('pickup', True)
    has_x_action = allow_converge or allow_pickup

    # T pruning
    if action == 'T':
        if last_action == 'T':
            return True  # T->T
        if last_action == 'V':
            return True  # branches identical right after diverge, T is noop
        if ctrl.has_branched and _branch_key(ctrl.main_branch) == _branch_key(ctrl.sub_branch):
            return True  # branches are still symmetric

    # Pattern: V->C/I (branch then immediately merge)
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
        # Open area: move immediately (direction set as side effect, not logged)
        return not GameLogic.can_move(active, direction)

    if action == 'V':
        if ctrl.has_branched:
            return True
        # Also skip if player is not standing on a branch point
        active = ctrl.get_active_branch()
        terrain = active.terrain.get(active.player.pos)
        return terrain not in GameController.BRANCH_DECREMENT

    if action in ('C', 'T'):
        return not ctrl.has_branched  # can't merge/switch if not branched

    if action == 'I':
        if not ctrl.has_branched:
            return True
        focused = ctrl.get_active_branch()
        other = ctrl.sub_branch if ctrl.current_focus == 0 else ctrl.main_branch
        focused_held = set(focused.get_held_items())
        other_held = set(other.get_held_items())
        total_items = len(focused_held | other_held)
        capacity = Physics.effective_capacity(focused)

        # Inherit merge will fail.
        if total_items > capacity:
            return True
        # If other branch carries nothing, inherit is equivalent to normal merge C.
        if not other_held:
            return True
        return False

    if action in ('X', 'P', 'O'):
        active = ctrl.get_active_branch()
        px, py = active.player.pos
        dx, dy = active.player.direction
        front_pos = (px + dx, py + dy)
        holding = bool(active.get_held_items())

        if action == 'O':
            # X fully dominates O (holding -> drop path is identical).
            if has_x_action:
                return True
            if not holding:
                return True
            return Physics.collision_at(front_pos, active) > 0

        if action == 'P':
            if not allow_pickup:
                return True
            if Physics.effective_capacity(active, at_pos=active.player.pos) == 0:
                return True
            target = active.find_box_at(front_pos)
            if target is None:
                return True
            uids_at_front = {
                e.uid for e in active.entities
                if e.uid != 0
                and e.type == EntityType.BOX
                and e.pos == front_pos
                and Physics.grounded(e)
            }
            has_overlap = len(uids_at_front) >= 2
            # Rule: shadow/overlap must converge before pickup.
            if has_overlap or active.is_shadow(target.uid):
                return True
            # X fully dominates valid solid pickup.
            if has_x_action:
                return True
            return False

        # action == 'X'
        if holding:
            return Physics.collision_at(front_pos, active) > 0

        target = active.find_box_at(front_pos)
        if target is None:
            return True

        uids_at_front = {
            e.uid for e in active.entities
            if e.uid != 0
            and e.type == EntityType.BOX
            and e.pos == front_pos
            and Physics.grounded(e)
        }
        has_overlap = len(uids_at_front) >= 2

        # X converges on overlap/shadow; otherwise it falls back to pickup.
        if has_overlap or active.is_shadow(target.uid):
            return not allow_converge
        if not allow_pickup:
            return True
        return Physics.effective_capacity(active, at_pos=active.player.pos) == 0

    return False


def _legal_actions_for_state(ctrl: GameController, hints: dict) -> list:
    """Build legal candidate actions from system constraints for current state."""
    actions = ['U', 'D', 'L', 'R']
    active = ctrl.get_active_branch()
    terrain = active.terrain.get(active.player.pos)
    on_branch_point = terrain in GameController.BRANCH_DECREMENT

    # System-level legal actions are looked up from a precomputed table.
    actions.extend(
        _SYSTEM_ACTION_TABLE[(
            ctrl.has_branched,
            on_branch_point,
            bool(hints.get('diverge')),
            bool(hints.get('inherit')),
        )]
    )

    # X is only legal when it can trigger a valid system action.
    if hints.get('converge') or hints.get('pickup'):
        px, py = active.player.pos
        dx, dy = active.player.direction
        front_pos = (px + dx, py + dy)
        holding = bool(active.get_held_items())

        if holding:
            if Physics.collision_at(front_pos, active) <= 0:
                actions.append('X')
        else:
            target = active.find_box_at(front_pos)
            if target is not None:
                uids_at_front = {
                    e.uid for e in active.entities
                    if e.uid != 0
                    and e.type == EntityType.BOX
                    and e.pos == front_pos
                    and Physics.grounded(e)
                }
                has_overlap = len(uids_at_front) >= 2

                if has_overlap or active.is_shadow(target.uid):
                    if hints.get('converge'):
                        actions.append('X')
                else:
                    if hints.get('pickup') and Physics.effective_capacity(active, at_pos=active.player.pos) > 0:
                        actions.append('X')

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
    initial = GameController(source, solver_mode=True)
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
        actions = _legal_actions_for_state(ctrl, hints)
        for action in actions:
            if _is_noop(ctrl, action, last_action, hints):
                continue
            new_ctrl = ctrl.clone_for_solver()
            execute_action(new_ctrl, action, hints)

            if not new_ctrl.collapsed and not new_ctrl.victory:
                new_ctrl.update_physics()
            if not new_ctrl.victory:
                new_ctrl.check_victory()

            if new_ctrl.collapsed:
                continue

            # Fusion entities indicate an unintended state (shadow boxes pushed together).
            # Treat as failure to keep the search space tractable.
            active = new_ctrl.get_active_branch()
            if any(e.fused_from for e in active.entities):
                continue

            new_path = path + action

            if new_ctrl.victory:
                return new_path

            new_key = _state_key(new_ctrl)
            if new_key not in visited:
                visited.add(new_key)
                queue.append((new_ctrl, new_path))

    return None
