# main.py - Game Entry Point
#
# Level data + launcher for DIV Timeline Puzzle.

import json
import os
import sys

from game_window import run_game
from map_parser import parse_dual_layer


PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "progress.json")


EMPTY_HINTS = {
    "movement": False,
    "pickup": False,
    "diverge": False,
    "merge": False,
    "inherit": False,
}

WORLD1_HINTS = {
    "movement": True,
    "pickup": False,
    "diverge": True,  # unlock split in World 1
    "merge": True,
    "inherit": False,
}


def load_progress():
    """Load played levels from progress file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"played": []}
    return {"played": []}


def save_progress(progress):
    """Save played levels to progress file."""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def mark_as_played(level_id):
    """Mark a level as played (no longer first-time)."""
    progress = load_progress()
    if level_id not in progress["played"]:
        progress["played"].append(level_id)
        save_progress(progress)


def is_first_time(level_id):
    """Check if this is the first time playing this level."""
    progress = load_progress()
    return level_id not in progress["played"]


# Keep only 0-0 ~ 0-2
L0_0 = {
    "id": "0-0",
    "name": "Tutorial 0-0",
    "floor_map": """
.####.
..##..
......
.#..#.
.####.
.####G
""",
    "object_map": """
......
......
......
......
......
P.....
""",
    "hints": EMPTY_HINTS.copy(),
    'tutorial': {
        'title': '關卡 0-0：移動',
        'items': [
            '使用 W/A/S/D 或方向鍵移動角色',
            '角色會以藍色圓圈顯示，黑色箭頭顯示方向',
            '黑色區域是牆壁，無法通過',
            '黃色的 Goal 是目標點',
            '走到閃爍的 Goal 即可過關',
            '',
            '提示：按住方向鍵可以持續移動',
        ]
    }}

L0_1 = {
    "id": "0-1",
    "name": "Tutorial 0-1",
    "floor_map": """
#G...#
#.##..
#.#...
#....#
#.####
#.####
""",
    "object_map": """
......
.B....
....B.
..B...
.B....
.P....
""",
    "hints": EMPTY_HINTS.copy(),
    'tutorial': {
        'title': '關卡 0-1：推動',
        'items': [
            '標記數字的有色方形是方塊',
            '面向方塊按移動可以推動方塊',
            '若方塊後方有牆壁或其它方塊，就無法推動',
            '利用推動來清出通往目標的路徑',
                        '',
            '提示：如果沒有面對方塊，朝方塊按下方向鍵會原地轉向',
        ]
    }}

L0_2 = {
    "id": "0-2",
    "name": "Tutorial 0-2",
    "floor_map": """
#S..##
...###
.#####
.##S.G
..##..
#....#
""",
    "object_map": """
..BP..
......
......
....B.
......
......
""",
    "hints": EMPTY_HINTS.copy(),
    'tutorial': {
        'title': '關卡 0-2：目標',
        'items': [
            '灰色地磚是開關',
            '將方塊推到開關後會壓下開關變綠色',
            '黃色的 Goal 是目標點',
            '當所有開關都壓下，Goal就會啟動',
        ]
    }
}


TUTORIAL_LEVELS = [L0_0, L0_1, L0_2]
MAIN_LEVELS = [
    {
        "id": "1-1",
        "name": "Level 1-1",
        "floor_map": """
######
#.vG##
#S.S##
######
######
######
""",
        "object_map": """
......
.P....
..B...
......
......
......
""",
        "hints": WORLD1_HINTS.copy(),
    'tutorial': {
        'title': '關卡 1-1：分裂',
        'items': [
            '綠色的點是 分裂點',
            '站在分裂點上，再按 V 鍵可以分裂，複製兩個平行空間',

            '再按 V 可以合併兩個空間'
            '合併後，方塊會保持壓住開關的狀態',
            '',
            '提示：按 Tab 鍵可以切換視角',

        ]
    }

    },
    {
        "id": "1-2",
        "name": "Level 1-2",
        "floor_map": """
######
#...##
#v.S##
###G##
######
######
""",
        "object_map": """
......
......
.PB...
......
......
......
""",
        "hints": WORLD1_HINTS.copy(),
        "tutorial": None,
    },
    {
        "id": "1-3",
        "name": "Level 1-3",
        "floor_map": """
######
######
.v..G#
######
######
######
""",
        "object_map": """
......
......
P.B...
......
......
......
""",
        "hints": WORLD1_HINTS.copy(),
    'tutorial': {
        'title': '1-3：收束',
        'items': [
            '如果方塊在不同位置合併，將變成殘影',
            '殘影是不可推動的障礙',
            '對著殘影按下SPACE可破壞其它殘影，並且回復成實體',
            '',
            '提示：可收束的殘影會有虛線連結到目標',

        ]
    }    },
    {
        "id": "1-4",
        "name": "Level 1-4",
        "floor_map": """
######
###.##
#.v.G#
###S##
######
######
""",
        "object_map": """
......
......
.P.B..
......
......
......
""",
        "hints": WORLD1_HINTS.copy(),
        "tutorial": None,
    },
    {
        "id": "1-5",
        "name": "Level 1-5",
        "floor_map": """
######
##.#.#
#...G#
#v.#S#
######
######
""",
        "object_map": """
......
......
.PB...
......
......
......
""",
        "hints": WORLD1_HINTS.copy(),
        "tutorial": None,
    },
    {
        "id": "1-6",
        "name": "Level 1-6",
        "floor_map": """
######
###.##
##v.G#
###S##
###v##
######
""",
        "object_map": """
......
......
...B..
...P..
......
......
""",
        "hints": WORLD1_HINTS.copy(),
        "tutorial": None,
    },
    {
        "id": "1-7",
        "name": "Level 1-7",
        "floor_map": """
######
##.#v#
#...G#
#v.#S#
######
######
""",
        "object_map": """
......
......
...BP.
......
......
......
""",
        "hints": WORLD1_HINTS.copy(),
        "tutorial": None,
    },
]


def launch(level):
    """Launch a level directly from level dict."""
    if not isinstance(level, dict) or "id" not in level:
        print(f"Error: Invalid level: {type(level)}")
        return

    level_id = level["id"]
    first_time = is_first_time(level_id)

    print(f"Starting: {level['name']} ({level_id})")
    mark_as_played(level_id)

    run_game(
        level["floor_map"],
        level["object_map"],
        hints=level.get("hints") or EMPTY_HINTS.copy(),
        tutorial=level.get("tutorial"),
        first_time=first_time,
    )


def launch_by_id(level_id: str):
    all_levels = {level["id"]: level for level in (TUTORIAL_LEVELS + MAIN_LEVELS)}
    if level_id not in all_levels:
        print(f"Error: Level {level_id} not found")
        print(f"Available levels: {', '.join(sorted(all_levels.keys()))}")
        return
    launch(all_levels[level_id])


def launch_tutorial(level_index: int = 0):
    if level_index < 0 or level_index >= len(TUTORIAL_LEVELS):
        print(f"Error: Tutorial level {level_index} not found")
        return
    launch(TUTORIAL_LEVELS[level_index])


def launch_level(level_index: int = 0):
    if level_index < 0 or level_index >= len(MAIN_LEVELS):
        print(f"Error: Level {level_index} not found")
        return
    launch(MAIN_LEVELS[level_index])


def _read_ascii_map_block(layer_name: str) -> str:
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


def launch_ascii_test_main():
    print("=" * 60)
    print("DIV Test Main - Paste ASCII Maps")
    print("=" * 60)
    print("Floor symbols: . # S c v V x X G H")
    print("Object symbols: . P B")

    floor_map = _read_ascii_map_block("floor")
    object_map = _read_ascii_map_block("object")
    parse_dual_layer(floor_map, object_map)
    run_game(floor_map, object_map, hints=EMPTY_HINTS.copy(), tutorial=None, first_time=False)


if __name__ == "__main__":
    try:
        if "--ascii" in sys.argv:
            launch_ascii_test_main()
        else:
            from level_selector import run_level_selector

            run_level_selector()
    except Exception as e:
        print(f"Launch failed: {e}")
