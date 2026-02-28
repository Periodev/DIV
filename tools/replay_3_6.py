import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from level_constructor import load_main_levels
from map_parser import parse_level
from game_controller import GameController

# User-provided solution to trace
SOLUTION = "RRPRLODDVUULPDOTCUVXPLLTCVXUULLLC"

DIR_MAP = {
    'R': (1, 0), 'L': (-1, 0), 'U': (0, -1), 'D': (0, 1),
}

levels = load_main_levels()
lv = levels[28]  # 3-6 Hand over (flat index 28)

parsed = parse_level(
    lv['id'], lv['name'], lv.get('objective', {}).get('title', lv['name']),
    lv['floor_map'], lv['object_map'], lv.get('hints')
)
source = parsed['source']


def run_solution(solution, label):
    ctrl = GameController(source)

    def snapshot(ctrl, step_label):
        b = ctrl.get_active_branch()
        p = b.player
        boxes = [e for e in b.entities if e.uid != 0]
        # holder field on an entity = uid of who carries it (None = not held)
        # player is "holding" if any entity has holder == 0 (player uid)
        held_uids = b.get_held_items()
        carrying = bool(held_uids)

        focus_name    = 'sub' if ctrl.current_focus == 1 else 'main'
        branches_name = 'main+sub' if ctrl.has_branched else 'main'
        pos_info      = f"player@{p.pos}"
        charge_info   = f"div_pts={ctrl.div_points}"
        carry_info    = f"holding={'box(uid=' + str(held_uids) + ')' if carrying else 'none'}"
        box_positions = [(e.pos, 'held' if e.holder == 0 else 'free') for e in boxes]
        victory_flag  = " <<< VICTORY" if ctrl.victory else ""
        collapsed_flag = " <<< COLLAPSED" if ctrl.collapsed else ""

        print(f"[{step_label:>22}] {pos_info} {charge_info} {carry_info} "
              f"boxes={box_positions} branches={branches_name} focus={focus_name}"
              f"{victory_flag}{collapsed_flag}")

    print(f"=== {label} ===")
    print(f"Solution: {solution}  ({len(solution)} chars)")
    snapshot(ctrl, "START")

    for i, ch in enumerate(solution):
        if ch in DIR_MAP:
            ctrl.handle_move(DIR_MAP[ch])
        elif ch == 'V':
            ctrl.try_branch()
        elif ch == 'M':
            ctrl.try_merge()
        elif ch == 'T':
            ctrl.switch_focus()
        elif ch == 'P':
            ctrl.handle_pickup()
        elif ch == 'O':
            ctrl.handle_drop()
        elif ch == 'X':
            ctrl.try_fetch_merge()
        else:
            print(f"  [WARNING] Unknown char: {ch!r}")

        snapshot(ctrl, f"step {i+1:02d} ({ch})")

    print()
    b = ctrl.get_active_branch()
    print(f"Final player pos: {b.player.pos}")
    print(f"All switches activated: {b.all_switches_activated()}")
    print(f"Victory: {ctrl.victory}")
    print(f"Collapsed: {ctrl.collapsed}")
    print(f"Input log recorded: {''.join(ctrl.input_log)}")
    print()


print("Level: 3-6 Hand over")
print("Map:  ###S  (y=0)")
print("      GcS.  (y=1)   G=goal  c=no_carry  S=switch  x=branch3  #=wall")
print("      ###c  (y=2)")
print("      ##Sx  (y=3)")
print("Objects: P@(1,1)  B@(2,1)")
print()

run_solution(SOLUTION, "User solution")
