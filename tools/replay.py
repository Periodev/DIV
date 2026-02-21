# replay.py - Replay tool entry point
#
# Usage:
#   python replay.py <level_id> <sequence> [--pause]
#   python replay.py 1-1 RRRDVTLLL

import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from level_constructor import MAIN_LEVELS


def find_level(level_id: str) -> dict:
    for level in MAIN_LEVELS:
        if level['id'] == level_id:
            return level
    return None


def launch_replay(level: dict, sequence: str, auto_play: bool = True):
    """Launch a replay window for a level and sequence."""
    try:
        import arcade
        from render_arc import WINDOW_WIDTH, WINDOW_HEIGHT
        from replay_core import Replayer
        from replay_view import ReplayView
    except ModuleNotFoundError as e:
        if e.name == 'arcade':
            print("Replay unavailable: missing dependency 'arcade'.")
            return False
        raise

    sequence = sequence.upper()
    replayer = Replayer(level)
    replayer.load(sequence)

    title = f"{level['id']} {level['name']}  |  {sequence}"
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, f"Replay - {level['name']}")
    view = ReplayView(replayer, title=title, auto_play_start=auto_play)
    window.show_view(view)
    arcade.run()
    return True


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python replay.py <level_id> <sequence> [--pause]")
        print("Example: python replay.py 1-1 RRRDVTLLL")
        print()
        print("Input characters:")
        print("  U D L R  move")
        print("  V        branch (diverge)")
        print("  C        normal merge")
        print("  F        fetch merge")
        print("  T        switch focus (Tab)")
        print("  X        adaptive action (converge / pickup)")
        print("  P        pickup")
        print("  O        drop")
        sys.exit(1)

    level_id = sys.argv[1]
    sequence = sys.argv[2]
    flags = set(sys.argv[3:])
    auto_play = '--pause' not in flags

    level = find_level(level_id)
    if not level:
        print(f"Level '{level_id}' not found.")
        print(f"Available: {[lv['id'] for lv in MAIN_LEVELS]}")
        sys.exit(1)

    ok = launch_replay(level, sequence, auto_play=auto_play)
    if not ok:
        sys.exit(2)

