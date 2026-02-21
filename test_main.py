"""Test entry point: inline map editing or manual ASCII input."""

import arcade
from game_window import GameView
from map_parser import parse_dual_layer
from render_arc import WINDOW_WIDTH, WINDOW_HEIGHT


TEST_HINTS = {
    "pickup": True,
    "diverge": True,
    "converge": True,
    "fetch": True,
}

# Set to True for fast iteration by editing maps in this file.
USE_INLINE_MAP = True

floor_map = '''
####S
####v
Gv.cc
####S
#####
'''

object_map = '''
.....
.....
P.B..
.....
.....
'''


def read_ascii_map_block(layer_name: str) -> str:
    print(f"\nPaste {layer_name} map (finish with line: END)")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        raise ValueError(f"{layer_name} map is empty")
    return text


def _normalize_map_block(raw: str) -> str:
    lines = [line.rstrip() for line in raw.strip("\n").splitlines() if line.strip()]
    if not lines:
        raise ValueError("Map is empty")
    return "\n".join(lines)


def launch_ascii_test_main():
    print("=" * 60)
    print("DIV Test Main")
    print("=" * 60)
    print("Floor symbols: . # S c v V x X G H")
    print("Object symbols: . P B")

    if USE_INLINE_MAP:
        print("Mode: inline map (edit floor_map/object_map in test_main.py)")
        floor = _normalize_map_block(floor_map)
        objects = _normalize_map_block(object_map)
    else:
        print("Mode: manual input")
        floor = read_ascii_map_block("floor")
        objects = read_ascii_map_block("object")

    parse_dual_layer(floor, objects)

    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, "div - test")
    view = GameView(
        floor, objects,
        hints=TEST_HINTS,
        first_time=False,
    )
    window.show_view(view)
    arcade.run()


if __name__ == "__main__":
    try:
        launch_ascii_test_main()
    except Exception as e:
        print(f"Launch failed: {e}")

