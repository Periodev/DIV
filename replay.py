# replay.py - Replay tool entry point
#
# Usage:
#   python replay.py <level_id> <sequence>
#   python replay.py 1-1 RRRDVTLLL

import sys
import arcade
from level_constructor import MAIN_LEVELS
from render_arc import WINDOW_WIDTH, WINDOW_HEIGHT
from replay_core import Replayer
from replay_view import ReplayView


def find_level(level_id: str) -> dict:
    for level in MAIN_LEVELS:
        if level['id'] == level_id:
            return level
    return None


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python replay.py <level_id> <sequence>")
        print("Example: python replay.py 1-1 RRRDVTLLL")
        print()
        print("Input characters:")
        print("  U D L R  — move")
        print("  V        — branch (diverge)")
        print("  C        — normal merge")
        print("  I        — inherit merge")
        print("  T        — switch focus (Tab)")
        print("  X        — adaptive action (converge / pickup)")
        print("  P        — pickup")
        print("  O        — drop")
        sys.exit(1)

    level_id = sys.argv[1]
    sequence = sys.argv[2].upper()

    level = find_level(level_id)
    if not level:
        print(f"Level '{level_id}' not found.")
        print(f"Available: {[lv['id'] for lv in MAIN_LEVELS]}")
        sys.exit(1)

    replayer = Replayer(level)
    replayer.load(sequence)

    title = f"{level['id']} {level['name']}  |  {sequence}"
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, f"Replay — {level['name']}")
    view = ReplayView(replayer, title=title)
    window.show_view(view)
    arcade.run()
