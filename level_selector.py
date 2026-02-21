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
TAB_ACTIVE_COLOR = (96, 165, 250)
TAB_ACTIVE_BG = (30, 60, 100)
TAB_BG = (35, 40, 50)

TITLE_Y = 670
TAB_BAR_Y = 620       # zone tab strip
GRID_START_Y = 580    # first row of level cells
ZONE_TITLE_GAP = 0    # no repeated zone title needed (shown in tab)
CELL_HEIGHT = 42
CELL_GAP_X = 10
ROW_GAP = 8
GRID_LEFT = 40
GRID_RIGHT = 40
COLUMNS = 3
TAB_HEIGHT = 32
TAB_PAD_X = 18


def _world_key(level_id: str):
    parts = level_id.split("-")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return (999, 999)


class LevelSelectorWindow(arcade.Window):
    """Graphical level selector window — zone-paged layout."""

    def __init__(self):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, "DIV - Level Selector")

        all_levels = TUTORIAL_LEVELS + MAIN_LEVELS
        all_levels.sort(key=lambda lv: _world_key(lv["id"]))
        self.levels = all_levels

        progress = load_progress()
        self.played_set = set(progress.get("played", []))
        self.text_cache = {}

        # Build zone list
        grouped = {}
        for idx, lv in enumerate(self.levels):
            w = lv["id"].split("-")[0]
            grouped.setdefault(w, []).append(idx)
        self.sorted_worlds = sorted(grouped.keys(), key=lambda x: int(x) if x.isdigit() else 999)
        self.world_indices = {w: grouped[w] for w in self.sorted_worlds}

        self.current_zone = 0          # index into sorted_worlds
        self.current_index = 0         # index into self.levels
        self.nav_rows = []             # rows for current zone
        self.index_pos = {}            # level index -> (row, col) within zone

        self._enter_zone(0)
        arcade.set_background_color(BACKGROUND_COLOR)

    # ------------------------------------------------------------------ layout

    def _enter_zone(self, zone_idx: int, preferred_col: int = 0):
        """Switch to zone and rebuild nav structures; try to keep column."""
        self.current_zone = zone_idx % len(self.sorted_worlds)
        world = self.sorted_worlds[self.current_zone]
        indices = self.world_indices[world]

        self.nav_rows = [indices[i:i + COLUMNS] for i in range(0, len(indices), COLUMNS)]
        self.index_pos = {}
        for r, row in enumerate(self.nav_rows):
            for c, idx in enumerate(row):
                self.index_pos[idx] = (r, c)

        # Place cursor at (row=0, preferred_col clamped)
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

        # Footer hint
        self._draw_text(
            "Arrows: select   Tab/Shift+Tab: zone   Enter/Space: start   Esc: exit",
            WINDOW_WIDTH // 2, 28,
            SECTION_COLOR, 11, anchor_x="center",
        )

    def _draw_zone_tabs(self):
        """Draw horizontal zone tab strip."""
        n = len(self.sorted_worlds)
        tab_total = WINDOW_WIDTH - GRID_LEFT - GRID_RIGHT
        tab_w = (tab_total - (n - 1) * 4) // n

        for i, world in enumerate(self.sorted_worlds):
            x = GRID_LEFT + i * (tab_w + 4)
            y = TAB_BAR_Y
            active = (i == self.current_zone)
            bg = TAB_ACTIVE_BG if active else TAB_BG
            arcade.draw_lrbt_rectangle_filled(x, x + tab_w, y - TAB_HEIGHT, y, bg)
            if active:
                arcade.draw_lrbt_rectangle_outline(x, x + tab_w, y - TAB_HEIGHT, y,
                                                   TAB_ACTIVE_COLOR, 2)
            label = f"Zone {world}"
            color = TAB_ACTIVE_COLOR if active else SECTION_COLOR
            self._draw_text(label, x + tab_w // 2, y - TAB_HEIGHT // 2,
                            color, 12, anchor_x="center", anchor_y="center", bold=active)

    def _draw_level_item(self, index, x, y, width, height):
        level = self.levels[index]
        is_current = index == self.current_index
        is_played = level["id"] in self.played_set

        bg = HIGHLIGHT_BG if is_current else (31, 39, 52)
        arcade.draw_lrbt_rectangle_filled(x, x + width, y - height, y, bg)

        marker = "Done" if is_played else "    "
        marker_color = PLAYED_COLOR if is_played else TEXT_COLOR
        self._draw_text(marker, x + 6, y - 9, marker_color, 10, anchor_y="center")

        text = level["name"]
        color = HIGHLIGHT_COLOR if is_current else TEXT_COLOR
        font_size = 11 if is_current else 10
        self._draw_text(text, x + 6, y - 27, color, font_size, anchor_y="center")

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
            cached = self.text_cache[cache_key]
            cached.x = x
            cached.y = y
            cached.color = color
        self.text_cache[cache_key].draw()

    # ------------------------------------------------------------------ input

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.exit()
        elif key == arcade.key.TAB:
            _, col = self.index_pos[self.current_index]
            if modifiers & arcade.key.MOD_SHIFT:
                self._enter_zone(self.current_zone - 1, preferred_col=col)
            else:
                self._enter_zone(self.current_zone + 1, preferred_col=col)
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
