# solver_core.py - BFS / Fast(A*) level solver (pure logic, no Arcade dependency)

import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from collections import deque
from array import array
from heapq import heappop, heappush
import struct
from map_parser import parse_dual_layer
from game_controller import GameController
from game_logic import GameLogic
from replay_core import execute_action, DIRECTION_MAP
from timeline_system import Physics, EntityType, TerrainType

_OPPOSITES = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}


def _build_system_action_table() -> dict:
    """Precompute legal system actions (V/C/T/F) by coarse state flags."""
    table = {}
    for has_branched in (False, True):
        for has_div_points in (False, True):
            for allow_diverge in (False, True):
                for allow_fetch in (False, True):
                    actions = []
                    if not has_branched:
                        if allow_diverge and has_div_points:
                            actions.append('V')
                    else:
                        actions.extend(['M', 'T'])
                        if allow_fetch:
                            actions.append('F')
                    table[(has_branched, has_div_points, allow_diverge, allow_fetch)] = tuple(actions)
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
    # Scan entities once; use module-level frozenset to avoid per-call set allocation.
    px, py = b.player.pos
    for e in b.entities:
        if e.type == EntityType.BOX and Physics.grounded(e):
            ex, ey = e.pos
            if (ex - px, ey - py) in _ADJACENT_DELTAS:
                return b.player.direction

    # No nearby interaction target: orientation is behaviorally irrelevant.
    return (0, 0)


def _has_any_box_instance_at(b, pos: tuple[int, int]) -> bool:
    """Check for any box instance at pos, including underground (z = -1)."""
    if b is None:
        return False
    for e in b.entities:
        if e.type == EntityType.BOX and e.pos == pos:
            return True
    return False


def _has_fused_entity(branch) -> bool:
    """Return True if any entity in the branch has fused_from set."""
    for e in branch.entities:
        if e.fused_from:
            return True
    return False


# Cardinal delta set for adjacency check (avoids per-call abs() calls).
_ADJACENT_DELTAS = frozenset(((0, -1), (0, 1), (-1, 0), (1, 0)))

# Pre-compiled struct formats for state key encoding.
# Layout: i32 uid, i16 pos[0], i16 pos[1], i8 z, u8 is_box, i32 holder, u16 fused_count
_ENTITY_STRUCT = struct.Struct('<ihhbBiH')
# Layout: i16 pos[0], i16 pos[1], i8 dir[0], i8 dir[1], u16 entity_count
_BRANCH_HEADER_STRUCT = struct.Struct('<hhbbH')


def _encode_entity_key(entity) -> bytes:
    """Compact, stable per-entity encoding for state hashing."""
    holder = -1 if entity.holder is None else entity.holder
    fused = entity.fused_from
    is_box = 1 if entity.type == EntityType.BOX else 0

    if not fused:
        return _ENTITY_STRUCT.pack(
            entity.uid, entity.pos[0], entity.pos[1], int(entity.z), is_box, holder, 0
        )

    fused_ids = sorted(fused)
    n = len(fused_ids)
    return struct.pack(
        f'<ihhbBiH{n}i',
        entity.uid, entity.pos[0], entity.pos[1], int(entity.z), is_box, holder, n, *fused_ids
    )


def _branch_key(b) -> bytes | None:
    """Compact, hashable snapshot for one branch."""
    if b is None:
        return None

    direction = _canonical_direction(b)
    # Keep historical semantics: identical entity records are deduplicated.
    # This intentionally merges states that differ only by duplicate instances.
    entities = sorted({_encode_entity_key(e) for e in b.entities})

    header = _BRANCH_HEADER_STRUCT.pack(
        b.player.pos[0], b.player.pos[1], direction[0], direction[1], len(entities)
    )
    return header + b''.join(entities)


def _state_key(c: GameController) -> bytes:
    """Compact snapshot of controller state (terrain is fixed, excluded)."""
    main_key = _branch_key(c.main_branch) or b''
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

    sub_key = sub_key or b''

    data = bytearray()
    data.append(1 if c.has_branched else 0)
    data.append(focus_key & 0xFF)
    data.extend(c.div_points.to_bytes(2, 'little', signed=False))
    data.extend(len(main_key).to_bytes(4, 'little', signed=False))
    data.extend(main_key)
    data.extend(len(sub_key).to_bytes(4, 'little', signed=False))
    data.extend(sub_key)
    return bytes(data)


def _is_noop(ctrl: GameController, action: str, last_action: str = None,
             hints: dict | None = None, raw_path: str = '') -> bool:
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

    # Pattern: V->C/F (branch then immediately merge)
    if action in ('M', 'F') and last_action == 'V':
        return True

    # Short oscillation pruning: ABAB on system actions (e.g., TCTC, TFTF).
    if raw_path and len(raw_path) >= 3:
        a = raw_path[-3]
        b = raw_path[-2]
        c = raw_path[-1]
        d = action
        if a == c and b == d:
            pair = (a, b)
            if pair in {
                ('T', 'M'), ('M', 'T'),
                ('T', 'F'), ('F', 'T'),
                ('M', 'F'), ('F', 'M'),
            }:
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
            # Keep reverse moves when the prior step pushed a box into a hole:
            # the box becomes underground (z=-1) and isn't visible to has_box_at().
            if not _has_any_box_instance_at(active, pushed_pos):
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
        return ctrl.div_points < 1

    if action in ('M', 'T'):
        return not ctrl.has_branched  # can't merge/switch if not branched

    if action == 'F':
        if not ctrl.has_branched:
            return True
        focused = ctrl.get_active_branch()
        other = ctrl.sub_branch if ctrl.current_focus == 0 else ctrl.main_branch
        focused_held = set(focused.get_held_items())
        other_held = set(other.get_held_items())
        total_items = len(focused_held | other_held)
        capacity = Physics.effective_capacity(focused)

        # fetch merge will fail.
        if total_items > capacity:
            return True
        # If other branch carries nothing, fetch is equivalent to normal merge M.
        if not other_held:
            return True
        return False

    if action in ('C', 'P', 'O'):
        active = ctrl.get_active_branch()
        px, py = active.player.pos
        dx, dy = active.player.direction
        front_pos = (px + dx, py + dy)
        holding = bool(active.get_held_items())

        if action == 'O':
            # C fully dominates O (holding -> drop path is identical).
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
            # C fully dominates valid solid pickup.
            if has_x_action:
                return True
            return False

        # action == 'C'
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


def _is_static_wall_or_oob(state, pos: tuple[int, int]) -> bool:
    """True if pos is out of bounds or a wall tile."""
    if not Physics.in_bound(pos, state):
        return True
    return state.terrain.get(pos) == TerrainType.WALL


def _has_dead_corner_box(state) -> bool:
    """Detect simple irreversible corner deadlock (non-switch grounded boxes).

    NOTE: This heuristic is only sound in non-pickup rulesets. When pickup is
    enabled, cornered boxes can still be recovered by lifting them.
    """
    for e in state.entities:
        if e.uid == 0 or e.type != EntityType.BOX:
            continue
        if not Physics.grounded(e) or e.collision <= 0:
            continue
        if e.holder is not None:
            continue
        if state.is_shadow(e.uid):
            continue

        pos = e.pos
        if state.terrain.get(pos) == TerrainType.SWITCH:
            continue

        left = _is_static_wall_or_oob(state, (pos[0] - 1, pos[1]))
        right = _is_static_wall_or_oob(state, (pos[0] + 1, pos[1]))
        up = _is_static_wall_or_oob(state, (pos[0], pos[1] - 1))
        down = _is_static_wall_or_oob(state, (pos[0], pos[1] + 1))
        if (left and up) or (left and down) or (right and up) or (right and down):
            return True
    return False


def _switches_feasible(ctrl: GameController) -> bool:
    """Upper-bound check: return False if switches cannot all be activated.

    A box can shadow-cover up to (div_points + 1) switch positions via diverge.
    Shadow instances are intentionally double-counted to keep the bound loose (safe).
    Bug note: held boxes (z >= 0 but holder != None) are included because they
    can still be dropped onto switches.
    """
    if ctrl.has_branched:
        preview = ctrl.get_merge_preview()
    else:
        preview = ctrl.get_active_branch()

    unlit = sum(
        1 for pos, t in preview.terrain.items()
        if t == TerrainType.SWITCH and not preview.switch_activated(pos)
    )
    if unlit == 0:
        return True

    # Count non-underground boxes (z >= 0 covers grounded z=0 and held z=1).
    # Shadow duplicates are included deliberately — overcounting is safe here
    # because it keeps max_coverage high, avoiding false positives.
    boxes = sum(1 for e in preview.entities if e.type == EntityType.BOX and e.z >= 0)
    return unlit <= boxes * (ctrl.div_points + 1)


def _legal_actions_for_state(ctrl: GameController, hints: dict) -> list:
    """Build legal candidate actions from system constraints for current state."""
    actions = ['U', 'D', 'L', 'R']
    active = ctrl.get_active_branch()

    # System-level legal actions are looked up from a precomputed table.
    actions.extend(
        _SYSTEM_ACTION_TABLE[(
            ctrl.has_branched,
            ctrl.div_points > 0,
            bool(hints.get('diverge')),
            bool(hints.get('fetch')),
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
                actions.append('C')
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
                        actions.append('C')
                else:
                    if hints.get('pickup') and Physics.effective_capacity(active, at_pos=active.player.pos) > 0:
                        actions.append('C')

    return actions


def _output_char_for_action(ctrl: GameController, action: str) -> str:
    """Map internal action to user-facing bottom-level action symbol."""
    if action != 'C':
        return action

    active = ctrl.get_active_branch()
    if active.get_held_items():
        return 'O'

    px, py = active.player.pos
    dx, dy = active.player.direction
    front_pos = (px + dx, py + dy)
    target = active.find_box_at(front_pos)
    if target is None:
        return 'C'

    uids_at_front = {
        e.uid for e in active.entities
        if e.uid != 0
        and e.type == EntityType.BOX
        and e.pos == front_pos
        and Physics.grounded(e)
    }
    has_overlap = len(uids_at_front) >= 2
    if has_overlap or active.is_shadow(target.uid):
        return 'C'
    return 'P'


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _heuristic(ctrl: GameController, goal_positions: list[tuple[int, int]]) -> int:
    """Heuristic for fast mode (weighted A*)."""
    active = ctrl.get_active_branch()
    player_pos = active.player.pos

    if goal_positions:
        goal_dist = min(_manhattan(player_pos, goal_pos) for goal_pos in goal_positions)
    else:
        goal_dist = 0

    # Prefer states closer to satisfying switch conditions.
    if ctrl.has_branched:
        preview = ctrl.get_merge_preview()
    else:
        preview = active
    unlit_switches = sum(
        1 for pos, terrain in preview.terrain.items()
        if terrain == TerrainType.SWITCH and not preview.switch_activated(pos)
    )

    branched_penalty = 2 if ctrl.has_branched else 0
    carrying_penalty = 1 if active.get_held_items() else 0
    return goal_dist + 3 * unlit_switches + branched_penalty + carrying_penalty


def _ordered_actions(ctrl: GameController, hints: dict) -> list[str]:
    """Action ordering for fast mode to improve early solution quality."""
    actions = _legal_actions_for_state(ctrl, hints)
    priority = {
        'C': 0, 'P': 0, 'O': 0,
        'U': 1, 'D': 1, 'L': 1, 'R': 1,
        'V': 2,
        'M': 3, 'F': 3,
        'T': 4,
    }
    return sorted(actions, key=lambda action: (priority.get(action, 9), action))


def _next_tail(raw_tail: str, action: str, keep: int = 3) -> str:
    """Keep only the latest N raw actions for local pattern checks."""
    tail = raw_tail + action
    if len(tail) > keep:
        return tail[-keep:]
    return tail


def _rebuild_output_path(parents, out_actions: bytearray, node_id: int) -> str:
    """Reconstruct output sequence from parent chain."""
    chars = []
    while node_id != 0:
        chars.append(chr(out_actions[node_id]))
        node_id = parents[node_id]
    chars.reverse()
    return ''.join(chars)


def solve_fast(level_dict: dict, max_depth: int = 60,
               progress_cb=None, weight: float = 1.6) -> str | None:
    """Weighted A* solver (f = g + weight * h).

    Returns a valid solution quickly in hard levels; does not guarantee shortest path.
    """
    hints = level_dict.get('hints') or {
        'diverge': True, 'converge': True, 'pickup': True, 'fetch': True,
    }
    source = parse_dual_layer(level_dict['floor_map'], level_dict['object_map'])
    initial = GameController(source, solver_mode=True)
    goal_positions = [pos for pos, terrain in source.terrain.items() if terrain == TerrainType.GOAL]

    start_key = _state_key(initial)
    best_g = {start_key: 0}

    # Node storage for reconstruction only (node 0 is root).
    parents = array('i', [-1])
    out_actions = bytearray(b'\0')

    # Heap item: (f, g, tie, controller, node_id, raw_tail, t_in_cycle)
    # t_in_cycle: number of T actions since the last V/C/F (CRDT canonical form)
    heap = []
    tie = 0
    start_h = _heuristic(initial, goal_positions)
    heappush(heap, (weight * start_h, 0, tie, initial, 0, '', 0))
    popped = 0

    while heap:
        _, g, _, ctrl, node_id, raw_tail, t_in_cycle = heappop(heap)
        popped += 1
        if progress_cb and popped % 10000 == 0:
            progress_cb(popped, len(best_g))

        key = _state_key(ctrl)
        if g != best_g.get(key):
            continue  # stale queue entry

        if g >= max_depth:
            continue

        last_action = raw_tail[-1] if raw_tail else None
        for action in _ordered_actions(ctrl, hints):
            if _is_noop(ctrl, action, last_action, hints, raw_tail):
                continue

            # CRDT canonical form: within each V…C cycle, allow at most one focus
            # switch (T). This eliminates interleaved M-T-N-T-M sequences that
            # are equivalent to the canonical M-T-(M+N) ordering.
            if action == 'T' and t_in_cycle >= 1:
                continue

            new_ctrl = ctrl.clone_for_solver()
            output_char = _output_char_for_action(ctrl, action)
            execute_action(new_ctrl, action, hints)

            if not new_ctrl.collapsed and not new_ctrl.victory:
                new_ctrl.update_physics()
            if not new_ctrl.victory:
                new_ctrl.check_victory()

            if new_ctrl.collapsed:
                continue

            active = new_ctrl.get_active_branch()
            if _has_fused_entity(active):
                continue
            if not hints.get('pickup', True) and not hints.get('diverge', True) \
                    and not active.all_switches_activated() and _has_dead_corner_box(active):
                continue
            if not _switches_feasible(new_ctrl):
                continue

            # Switch upper-bound: prune if boxes can't possibly cover remaining switches.
            if not _switches_feasible(new_ctrl):
                continue

            new_g = g + 1
            if new_g > max_depth:
                continue
            child_tail = _next_tail(raw_tail, action)

            # Update t_in_cycle for child node.
            if action in ('V', 'M', 'F'):
                new_t = 0
            elif action == 'T':
                new_t = t_in_cycle + 1
            else:
                new_t = t_in_cycle

            if new_ctrl.victory:
                child_id = len(parents)
                parents.append(node_id)
                out_actions.append(ord(output_char))
                return _rebuild_output_path(parents, out_actions, child_id)

            new_key = _state_key(new_ctrl)
            old_g = best_g.get(new_key)
            if old_g is not None and new_g >= old_g:
                continue

            best_g[new_key] = new_g
            tie += 1
            child_id = len(parents)
            parents.append(node_id)
            out_actions.append(ord(output_char))
            new_h = _heuristic(new_ctrl, goal_positions)
            heappush(heap, (new_g + weight * new_h, new_g, tie, new_ctrl, child_id, child_tail, new_t))

    return None


def solve(level_dict: dict, max_depth: int = 60,
          progress_cb=None) -> str | None:
    """BFS solver. Returns solution string or None if not found.

    Args:
        level_dict:   level data dict (floor_map, object_map, hints)
        max_depth:    maximum sequence length to search
        progress_cb:  optional callable(states_visited) for progress reporting
    """
    hints = level_dict.get('hints') or {
        'diverge': True, 'converge': True, 'pickup': True, 'fetch': True,
    }
    source = parse_dual_layer(level_dict['floor_map'], level_dict['object_map'])
    initial = GameController(source, solver_mode=True)
    # Node storage for reconstruction only (node 0 is root).
    parents = array('i', [-1])
    out_actions = bytearray(b'\0')

    # Queue item: (controller, node_id, depth, raw_tail, t_in_cycle)
    # t_in_cycle: number of T actions since the last V/C/F (CRDT canonical form)
    queue = deque([(initial, 0, 0, '', 0)])
    visited = {_state_key(initial)}
    count = 0

    while queue:
        ctrl, node_id, depth, raw_tail, t_in_cycle = queue.popleft()
        count += 1
        if progress_cb and count % 10000 == 0:
            progress_cb(count, len(visited))

        if depth >= max_depth:
            continue

        last_action = raw_tail[-1] if raw_tail else None
        actions = _legal_actions_for_state(ctrl, hints)
        for action in actions:
            if _is_noop(ctrl, action, last_action, hints, raw_tail):
                continue

            # CRDT canonical form: within each V…C cycle, allow at most one focus
            # switch (T). This eliminates interleaved M-T-N-T-M sequences that
            # are equivalent to the canonical M-T-(M+N) ordering.
            if action == 'T' and t_in_cycle >= 1:
                continue

            new_ctrl = ctrl.clone_for_solver()
            output_char = _output_char_for_action(ctrl, action)
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
            if _has_fused_entity(active):
                continue
            if not hints.get('pickup', True) and not hints.get('diverge', True) \
                    and not active.all_switches_activated() and _has_dead_corner_box(active):
                continue
            if not _switches_feasible(new_ctrl):
                continue

            # Switch upper-bound: prune if boxes can't possibly cover remaining switches.
            if not _switches_feasible(new_ctrl):
                continue

            new_depth = depth + 1
            child_tail = _next_tail(raw_tail, action)

            # Update t_in_cycle for child node.
            if action in ('V', 'M', 'F'):
                new_t = 0
            elif action == 'T':
                new_t = t_in_cycle + 1
            else:
                new_t = t_in_cycle

            if new_ctrl.victory:
                child_id = len(parents)
                parents.append(node_id)
                out_actions.append(ord(output_char))
                return _rebuild_output_path(parents, out_actions, child_id)

            new_key = _state_key(new_ctrl)
            if new_key not in visited:
                visited.add(new_key)
                child_id = len(parents)
                parents.append(node_id)
                out_actions.append(ord(output_char))
                queue.append((new_ctrl, child_id, new_depth, child_tail, new_t))

    return None

