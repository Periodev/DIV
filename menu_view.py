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
TAB_ACTIVE_COLOR = (96, 165, 250)
TAB_ACTIVE_BG = (30, 60, 100)
TAB_BG = (35, 40, 50)

TITLE_Y = 670
TAB_BAR_Y = 625        # zone tab strip top edge
TAB_HEIGHT = 30
GRID_START_Y = 578     # first row of level cells
CELL_HEIGHT = 40
CELL_GAP_X = 10
ROW_GAP = 6
GRID_LEFT = 40
GRID_RIGHT = 40
CELL_INDENT = 0
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
        self.text_cache = {}

        # Build per-world index groups
        grouped = {}
        for idx, lv in enumerate(self.levels):
            w = lv["id"].split("-")[0]
            grouped.setdefault(w, []).append(idx)
        self.sorted_worlds = sorted(grouped.keys(), key=lambda x: int(x) if x.isdigit() else 999)
        self.world_indices = {w: grouped[w] for w in self.sorted_worlds}

        # Derive starting zone from cursor_index
        self.current_index = cursor_index
        start_zone = 0
        for z, w in enumerate(self.sorted_worlds):
            if cursor_index in self.world_indices[w]:
                start_zone = z
                break

        self.current_zone = -1         # force rebuild
        self.nav_rows: list = []
        self.index_pos: dict = {}
        self._enter_zone(start_zone)

    def on_show_view(self):
        arcade.set_background_color(BACKGROUND_COLOR)

    # ------------------------------------------------------------------ layout

    def _enter_zone(self, zone_idx: int, preferred_col: int = 0):
        self.current_zone = zone_idx % len(self.sorted_worlds)
        world = self.sorted_worlds[self.current_zone]
        indices = self.world_indices[world]

        self.nav_rows = [indices[i:i + COLUMNS] for i in range(0, len(indices), COLUMNS)]
        self.index_pos = {}
        for r, row in enumerate(self.nav_rows):
            for c, idx in enumerate(row):
                self.index_pos[idx] = (r, c)

        # Only move cursor when it's not already inside this zone
        if self.current_index not in self.index_pos:
            first_row = self.nav_rows[0]
            col = min(preferred_col, len(first_row) - 1)
            self.current_index = first_row[col]

    # ------------------------------------------------------------------ draw

    def on_draw(self):
        self.clear()

        # Title
        self._draw_text(
            "DIV - Timeline Puzzle",
            WINDOW_WIDTH // 2, TITLE_Y,
            TITLE_COLOR, 26, anchor_x="center", bold=True,
        )

        # Zone tab bar
        self._draw_zone_tabs()

        # Level grid for current zone
        cell_width = (WINDOW_WIDTH - GRID_LEFT - GRID_RIGHT - (COLUMNS - 1) * CELL_GAP_X) // COLUMNS
        y = GRID_START_Y
        for row in self.nav_rows:
            for col, idx in enumerate(row):
                x = GRID_LEFT + col * (cell_width + CELL_GAP_X)
                self._draw_level_item(idx, x, y, cell_width, CELL_HEIGHT)
            y -= (CELL_HEIGHT + ROW_GAP)

        # Footer
        self._draw_text(
            "WASD / 方向鍵 選關  |  Tab 切換 Zone  |  Enter / Space 進入  |  Esc 離開",
            WINDOW_WIDTH // 2, 28,
            SECTION_COLOR, 12, anchor_x="center",
        )

    def _draw_zone_tabs(self):
        n = len(self.sorted_worlds)
        total_w = WINDOW_WIDTH - GRID_LEFT - GRID_RIGHT
        tab_w = (total_w - (n - 1) * 4) // n

        for i, world in enumerate(self.sorted_worlds):
            x = GRID_LEFT + i * (tab_w + 4)
            y = TAB_BAR_Y
            active = (i == self.current_zone)
            bg = TAB_ACTIVE_BG if active else TAB_BG
            arcade.draw_lrbt_rectangle_filled(x, x + tab_w, y - TAB_HEIGHT, y, bg)
            if active:
                arcade.draw_lrbt_rectangle_outline(
                    x, x + tab_w, y - TAB_HEIGHT, y, TAB_ACTIVE_COLOR, 2
                )
            label = f"Zone {world}"
            color = TAB_ACTIVE_COLOR if active else SECTION_COLOR
            self._draw_text(
                label, x + tab_w // 2, y - TAB_HEIGHT // 2,
                color, 12, anchor_x="center", anchor_y="center", bold=active,
            )

    def _draw_level_item(self, index, x, y, width, height):
        level = self.levels[index]
        is_current = index == self.current_index
        is_played = level["id"] in self.progress

        bg = HIGHLIGHT_BG if is_current else (31, 39, 52)
        arcade.draw_lrbt_rectangle_filled(x, x + width, y - height, y, bg)

        cy = y - height // 2

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

    # ------------------------------------------------------------------ input

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.exit()
        elif key == arcade.key.TAB:
            _, col = self.index_pos[self.current_index]
            delta = -1 if (modifiers & arcade.key.MOD_SHIFT) else 1
            self._enter_zone(self.current_zone + delta, preferred_col=col)
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
