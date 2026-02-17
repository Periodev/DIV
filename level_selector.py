# level_selector.py - Graphical Level Selector

import arcade
from level_constructor import MAIN_LEVELS
from main import TUTORIAL_LEVELS, load_progress, launch


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
WORLD_TITLE_GAP = 24
CELL_HEIGHT = 42
CELL_GAP_X = 10
ROW_GAP = 8
WORLD_GAP = 12
GRID_LEFT = 40
GRID_RIGHT = 40
COLUMNS = 3


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
        self.world_layout = []
        self.nav_rows = []
        self.index_pos = {}

        progress = load_progress()
        self.played_set = set(progress.get("played", []))
        self.text_cache = {}
        self._build_layout()

        arcade.set_background_color(BACKGROUND_COLOR)

    def _build_layout(self):
        grouped_indices = {}
        for idx, level in enumerate(self.levels):
            world = level["id"].split("-")[0]
            grouped_indices.setdefault(world, []).append(idx)

        self.world_layout = []
        self.nav_rows = []
        self.index_pos = {}
        row_cursor = 0

        sorted_worlds = sorted(grouped_indices.keys(), key=lambda x: int(x) if x.isdigit() else 999)
        for world in sorted_worlds:
            indices = grouped_indices[world]
            rows = [indices[i:i + COLUMNS] for i in range(0, len(indices), COLUMNS)]
            self.world_layout.append((world, rows))
            for row in rows:
                self.nav_rows.append(row)
                for col, idx in enumerate(row):
                    self.index_pos[idx] = (row_cursor, col)
                row_cursor += 1

    def on_draw(self):
        self.clear()

        self._draw_text(
            "DIV - Timeline Puzzle",
            WINDOW_WIDTH // 2,
            TITLE_Y,
            TITLE_COLOR,
            26,
            anchor_x="center",
            bold=True,
        )
        self._draw_text(
            "Arrow Keys Select  |  Enter/Space Start  |  Esc Exit",
            WINDOW_WIDTH // 2,
            28,
            SECTION_COLOR,
            12,
            anchor_x="center",
        )

        y = SECTION_START_Y
        cell_width = (WINDOW_WIDTH - GRID_LEFT - GRID_RIGHT - (COLUMNS - 1) * CELL_GAP_X) // COLUMNS

        for world, rows in self.world_layout:
            self._draw_text(f"Zone {world}", GRID_LEFT, y, SECTION_COLOR, 13, bold=True)
            y -= WORLD_TITLE_GAP
            for row in rows:
                for col, idx in enumerate(row):
                    x = GRID_LEFT + col * (cell_width + CELL_GAP_X)
                    self._draw_level_item(idx, x, y, cell_width, CELL_HEIGHT)
                y -= (CELL_HEIGHT + ROW_GAP)
            y -= WORLD_GAP

    def _draw_level_item(self, index, x, y, width, height):
        level = self.levels[index]
        is_current = index == self.current_index
        is_played = level["id"] in self.played_set

        if is_current:
            left = x
            right = x + width
            bottom = y - height
            top = y
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, HIGHLIGHT_BG)
        else:
            arcade.draw_lrbt_rectangle_filled(x, x + width, y - height, y, (31, 39, 52))

        marker = "Done" if is_played else "    "
        marker_color = PLAYED_COLOR if is_played else TEXT_COLOR
        self._draw_text(marker, x + 6, y - 9, marker_color, 10, anchor_y="center")

        text = level["name"]
        color = HIGHLIGHT_COLOR if is_current else TEXT_COLOR
        font_size = 11 if is_current else 10
        self._draw_text(text, x + 6, y - 27, color, font_size, anchor_y="center")

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
        elif key == arcade.key.LEFT:
            self._move_horizontal(-1)
        elif key == arcade.key.RIGHT:
            self._move_horizontal(1)
        elif key == arcade.key.UP:
            self._move_vertical(-1)
        elif key == arcade.key.DOWN:
            self._move_vertical(1)
        elif key in (arcade.key.ENTER, arcade.key.SPACE):
            selected_level = self.levels[self.current_index]
            self.close()
            launch(selected_level)

    def _move_horizontal(self, delta):
        row_idx, col_idx = self.index_pos[self.current_index]
        row = self.nav_rows[row_idx]
        new_col = col_idx + delta
        if 0 <= new_col < len(row):
            self.current_index = row[new_col]

    def _move_vertical(self, delta):
        row_idx, col_idx = self.index_pos[self.current_index]
        row_count = len(self.nav_rows)
        if row_count == 0:
            return

        new_row_idx = (row_idx + delta) % row_count
        new_row = self.nav_rows[new_row_idx]
        new_col = min(col_idx, len(new_row) - 1)
        self.current_index = new_row[new_col]


def run_level_selector():
    window = LevelSelectorWindow()
    arcade.run()


if __name__ == "__main__":
    run_level_selector()
