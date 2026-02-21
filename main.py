# main.py - Game Entry Point
#
# Level data and launcher for DIV Timeline Puzzle.

import json
import os

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


if __name__ == "__main__":
    from menu_view import MenuView

    all_levels = MAIN_LEVELS
    progress = set(load_progress().get("played", []))

    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, "DIV")
    menu_view = MenuView(all_levels, progress, cursor_index=0)
    window.show_view(menu_view)
    arcade.run()
