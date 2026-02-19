# menu_view.py - Level selector as arcade.View

import arcade
from render_arc import WINDOW_WIDTH, WINDOW_HEIGHT


BACKGROUND_COLOR = (20, 20, 25)
TEXT_COLOR = (220, 220, 220)
TITLE_COLOR = (96, 165, 250)
HIGHLIGHT_COLOR = (96, 165, 250)
HIGHLIGHT_BG = (40, 80, 120)
SECTION_COLOR = (150, 150, 150)
PLAYED_COLOR = (80, 200, 120)

TITLE_Y = 670
SECTION_START_Y = 610
WORLD_TITLE_GAP = 10   # tight gap between zone title and its own rows
CELL_HEIGHT = 40
CELL_GAP_X = 10
ROW_GAP = 6
WORLD_GAP = 22         # large gap before next zone title
GRID_LEFT = 40
GRID_RIGHT = 40
CELL_INDENT = 20       # indent level cells relative to Zone title
COLUMNS = 4


def _world_key(level_id: str):
    parts = level_id.split("-")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return (999, 999)


class MenuView(arcade.View):
    def __init__(self, all_levels: list, progress: set, cursor_index: int = 0):
        super().__init__()
        self.levels = sorted(all_levels, key=lambda lv: _world_key(lv["id"]))
        self.progress = progress
        self.current_index = cursor_index
        self.world_layout = []
        self.nav_rows = []
        self.index_pos = {}
        self.text_cache = {}
        self._build_layout()

    def on_show_view(self):
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

        sorted_worlds = sorted(
            grouped_indices.keys(), key=lambda x: int(x) if x.isdigit() else 999
        )
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
            WINDOW_WIDTH // 2, TITLE_Y,
            TITLE_COLOR, 26, anchor_x="center", bold=True,
        )
        self._draw_text(
            "WASD / Arrow Keys 選關  |  Enter / Space 進入  |  Esc 離開",
            WINDOW_WIDTH // 2, 28,
            SECTION_COLOR, 12, anchor_x="center",
        )

        y = SECTION_START_Y
        available = WINDOW_WIDTH - GRID_LEFT - GRID_RIGHT - CELL_INDENT
        grid_width = int(available * 0.90)
        cell_width = (grid_width - (COLUMNS - 1) * CELL_GAP_X) // COLUMNS
        cell_start_x = GRID_LEFT + CELL_INDENT

        for world, rows in self.world_layout:
            self._draw_text(f"Zone {world}", GRID_LEFT, y, SECTION_COLOR, 13, bold=True)
            y -= WORLD_TITLE_GAP
            for row in rows:
                for col, idx in enumerate(row):
                    x = cell_start_x + col * (cell_width + CELL_GAP_X)
                    self._draw_level_item(idx, x, y, cell_width, CELL_HEIGHT)
                y -= (CELL_HEIGHT + ROW_GAP)
            y -= WORLD_GAP

    def _draw_level_item(self, index, x, y, width, height):
        level = self.levels[index]
        is_current = index == self.current_index
        is_played = level["id"] in self.progress

        bg = HIGHLIGHT_BG if is_current else (31, 39, 52)
        arcade.draw_lrbt_rectangle_filled(x, x + width, y - height, y, bg)

        cy = y - height // 2  # vertical center of cell

        if is_played:
            self._draw_text("✓", x + 6, cy, PLAYED_COLOR, 15, anchor_y="center")

        color = HIGHLIGHT_COLOR if is_current else TEXT_COLOR
        font_size = 14 if is_current else 12
        self._draw_text(level["name"], x + 26, cy, color, font_size, anchor_y="center")

    def _draw_text(self, text, x, y, color, size,
                   anchor_x="left", anchor_y="baseline", bold=False):
        cache_key = f"{text}_{size}_{bold}_{anchor_x}_{anchor_y}"
        if cache_key not in self.text_cache:
            self.text_cache[cache_key] = arcade.Text(
                text, x, y, color, size,
                anchor_x=anchor_x, anchor_y=anchor_y,
                font_name="Arial", bold=bold,
            )
        else:
            t = self.text_cache[cache_key]
            t.x = x
            t.y = y
            t.color = color
        self.text_cache[cache_key].draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.exit()
        elif key in (arcade.key.LEFT, arcade.key.A):
            self._move_horizontal(-1)
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self._move_horizontal(1)
        elif key in (arcade.key.UP, arcade.key.W):
            self._move_vertical(-1)
        elif key in (arcade.key.DOWN, arcade.key.S):
            self._move_vertical(1)
        elif key in (arcade.key.ENTER, arcade.key.SPACE):
            self._launch_selected()

    def _launch_selected(self):
        from game_window import GameView
        from main import EMPTY_HINTS

        level = self.levels[self.current_index]
        level_id = level["id"]
        first_time = level_id not in self.progress

        game_view = GameView(
            level["floor_map"],
            level["object_map"],
            hints=level.get("hints") or EMPTY_HINTS.copy(),
            objective=level.get("objective"),
            first_time=first_time,
            cursor_index=self.current_index,
            all_levels=self.levels,
            progress=self.progress,
            level_id=level_id,
        )
        self.window.show_view(game_view)

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
        self.current_index = new_row[min(col_idx, len(new_row) - 1)]
