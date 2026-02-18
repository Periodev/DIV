# main.py - Game Entry Point
#
# Level data and launcher for DIV Timeline Puzzle.

import json
import os
import sys

import arcade
from render_arc import WINDOW_WIDTH, WINDOW_HEIGHT
from level_constructor import MAIN_LEVELS


PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "progress.json")


EMPTY_HINTS = {
    "diverge": False,
    "pickup": False,
    "converge": False,
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
    """Mark a level as played."""
    progress = load_progress()
    if level_id not in progress["played"]:
        progress["played"].append(level_id)
        save_progress(progress)


# Keep only 0-0 ~ 0-2
L0_0 = {
    "id": "0-0",
    "name": "Move 移動 ",
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
    'objective': {
        'title': '關卡 0-0：移動',
        'items': [
            '使用 W/A/S/D 或方向鍵移動角色',
            '角色是藍色圓圈，黑色箭頭代表方向',
            '黃色的 Goal 是終點',
            '',
            '任務 : 走到閃爍的 Goal 即可過關',
        ]
    }}

L0_1 = {
    "id": "0-1",
    "name": "Push 推動",
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
    'objective': {
        'title': '關卡 0-1：推動',
        'items': [
            '標記數字的方形色塊是方塊',
            '面向方塊按移動可以推動方塊',
            '若方塊後方有牆壁或其它方塊，就無法推動',
            '',
            '任務 : 推動方塊清出通往終點的路徑',
        ]
    }}

L0_2 = {
    "id": "0-2",
    "name": "Goal 目標",
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
    'objective': {
        'title': '關卡 0-2：目標',
        'items': [
            '有方形標記的灰色地磚是開關',
            '將方塊壓住開關可啟動',
            '當所有開關都壓下，Goal就會閃爍',
            '',
            '任務 : 壓住所有開關後走到終點',
        ]
    }
}


TUTORIAL_LEVELS = [L0_0, L0_1, L0_2]


if __name__ == "__main__":
    from menu_view import MenuView

    all_levels = TUTORIAL_LEVELS + MAIN_LEVELS
    progress = set(load_progress().get("played", []))

    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, "div - Timeline Puzzle")
    menu_view = MenuView(all_levels, progress, cursor_index=0)
    window.show_view(menu_view)
    arcade.run()
