# level_selector.py - Graphical Level Selector

import arcade
from main import TUTORIAL_LEVELS, MAIN_LEVELS, load_progress, launch


WINDOW_WIDTH = 820
WINDOW_HEIGHT = 720
BACKGROUND_COLOR = (20, 20, 25)

TEXT_COLOR = (220, 220, 220)
TITLE_COLOR = (96, 165, 250)
HIGHLIGHT_COLOR = (96, 165, 250)
HIGHLIGHT_BG = (40, 80, 120)
SECTION_COLOR = (150, 150, 150)
PLAYED_COLOR = (80, 200, 120)

TITLE_Y = 670
SECTION_START_Y = 610
LINE_HEIGHT = 34
INDENT = 110


def _world_key(level_id: str):
    parts = level_id.split("-")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return (999, 999)


class LevelSelectorWindow(arcade.Window):
    """Graphical level selector window."""

    def __init__(self):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, "DIV - Level Selector")

        self.levels = TUTORIAL_LEVELS + MAIN_LEVELS
        self.levels.sort(key=lambda lv: _world_key(lv["id"]))
        self.current_index = 0

        progress = load_progress()
        self.played_set = set(progress.get("played", []))
        self.text_cache = {}

        arcade.set_background_color(BACKGROUND_COLOR)

    def on_draw(self):
        self.clear()

        self._draw_text(
            "DIV - Timeline Puzzle",
            WINDOW_WIDTH // 2,
            TITLE_Y,
            TITLE_COLOR,
            32,
            anchor_x="center",
            bold=True,
        )
        self._draw_text(
            "Arrow Keys Select  |  Enter/Space Start  |  Esc Exit",
            WINDOW_WIDTH // 2,
            28,
            SECTION_COLOR,
            14,
            anchor_x="center",
        )

        y = SECTION_START_Y

        grouped_indices = {}
        for idx, level in enumerate(self.levels):
            world = level["id"].split("-")[0]
            grouped_indices.setdefault(world, []).append(idx)

        for world in sorted(grouped_indices.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            self._draw_text(f"World {world}", 50, y, SECTION_COLOR, 16, bold=True)
            y -= LINE_HEIGHT
            for idx in grouped_indices[world]:
                y = self._draw_level_item(idx, y)
            y -= 12

    def _draw_level_item(self, index, y):
        level = self.levels[index]
        is_current = index == self.current_index
        is_played = level["id"] in self.played_set

        if is_current:
            left = 40
            right = WINDOW_WIDTH - 40
            bottom = y - (LINE_HEIGHT - 5) // 2
            top = y + (LINE_HEIGHT - 5) // 2
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, HIGHLIGHT_BG)

        marker = "Done" if is_played else "    "
        marker_color = PLAYED_COLOR if is_played else TEXT_COLOR
        self._draw_text(marker, INDENT - 55, y, marker_color, 12, anchor_y="center")

        text = f"{level['id']}  {level['name']}"
        color = HIGHLIGHT_COLOR if is_current else TEXT_COLOR
        font_size = 16 if is_current else 14
        self._draw_text(text, INDENT, y, color, font_size, anchor_y="center")
        return y - LINE_HEIGHT

    def _draw_text(self, text, x, y, color, size, anchor_x="left", anchor_y="baseline", bold=False):
        cache_key = f"{text}_{size}_{bold}_{anchor_x}_{anchor_y}"
        if cache_key not in self.text_cache:
            self.text_cache[cache_key] = arcade.Text(
                text,
                x,
                y,
                color,
                size,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                font_name="Arial",
                bold=bold,
            )
        else:
            cached = self.text_cache[cache_key]
            cached.x = x
            cached.y = y
            cached.color = color

        self.text_cache[cache_key].draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.exit()
        elif key == arcade.key.UP:
            self.current_index = (self.current_index - 1) % len(self.levels)
        elif key == arcade.key.DOWN:
            self.current_index = (self.current_index + 1) % len(self.levels)
        elif key in (arcade.key.ENTER, arcade.key.SPACE):
            selected_level = self.levels[self.current_index]
            self.close()
            launch(selected_level)


def run_level_selector():
    window = LevelSelectorWindow()
    arcade.run()


if __name__ == "__main__":
    run_level_selector()
