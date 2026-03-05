# menu_view.py - Level selector: left-panel list + centre map preview

import arcade
from render_arc import ArcadeRenderer, WINDOW_WIDTH, WINDOW_HEIGHT
from presentation_model import ViewModelBuilder as _B

# ── Layout (top-down y: 0 = top of window) ───────────────────────────────────
LEFT_W      = 300       # left panel width
LPAD        = 12        # text left indent inside panel

TITLE_CY    = 30        # top-down centre-y of window title bar
ZONE_HDR_CY = 56        # top-down centre-y of zone header row
HDIVIDE_Y   = 72        # top-down y of horizontal rule under zone header
LIST_TOP    = 80        # top-down y of first list-item top edge
ITEM_H      = 28        # px per list item

FOOTER_CY   = WINDOW_HEIGHT - 14   # top-down centre-y of footer hint

# Preview position matches the real game's focused-branch grid exactly.
# Sourced live from presentation_model so they never drift.
GAME_GRID_PX = _B.GRID_PX    # 480 px  (CELL_SIZE=80 × GRID_SIZE=6)
GAME_X       = _B.CENTER_X   # 400 px  (focused grid left edge)
GAME_Y       = _B.CENTER_Y   # 120 px  (focused grid top edge, top-down)

# ── Colours ───────────────────────────────────────────────────────────────────
BG_C        = (20,  20,  25)
TEXT_C      = (220, 220, 220)
MUTED_C     = (120, 120, 130)
TITLE_C     = (96,  165, 250)
SEL_BG_C    = (40,  80,  120)
SEL_TEXT_C  = (96,  165, 250)
DONE_C      = (80,  200, 120)
DIV_C       = (50,  55,  65)
ZONE_C      = (150, 200, 255)


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
        self.renderer = ArcadeRenderer()
        self._text_cache: dict = {}

        # Zone grouping
        grouped: dict = {}
        for idx, lv in enumerate(self.levels):
            w = lv["id"].split("-")[0]
            grouped.setdefault(w, []).append(idx)
        self.sorted_worlds = sorted(grouped, key=lambda x: int(x) if x.isdigit() else 999)
        self.world_indices = {w: grouped[w] for w in self.sorted_worlds}

        # Pre-build initial BranchState for every level (map preview)
        self._states = self._prebuild_states()

        # Restore cursor + derive zone
        self.current_index = cursor_index
        self.current_zone = 0
        for z, w in enumerate(self.sorted_worlds):
            if cursor_index in self.world_indices[w]:
                self.current_zone = z
                break

    # ── Initialisation ────────────────────────────────────────────────────────

    def _prebuild_states(self) -> dict:
        """Parse every level once and cache its initial BranchState."""
        from map_parser import parse_dual_layer
        from game_controller import GameController
        states = {}
        for lv in self.levels:
            try:
                src  = parse_dual_layer(lv["floor_map"], lv["object_map"])
                ctrl = GameController(src, solver_mode=True)
                states[lv["id"]] = ctrl.main_branch
            except Exception:
                states[lv["id"]] = None
        return states

    def on_show_view(self):
        arcade.set_background_color(BG_C)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def on_draw(self):
        self.clear()

        # Window title
        self._t("DIV",
                WINDOW_WIDTH // 2, TITLE_CY, TITLE_C, 18, ax="center")

        # Vertical divider between panels
        arcade.draw_line(LEFT_W, 0, LEFT_W, WINDOW_HEIGHT, DIV_C, 1)

        self._draw_panel()
        self._draw_preview()

        # Footer hint
        self._t("↑↓ 選關  ←→ 切換 Zone  Enter/Space 進入  Esc 離開",
                WINDOW_WIDTH // 2, FOOTER_CY, MUTED_C, 11, ax="center")

    def _draw_panel(self):
        world = self.sorted_worlds[self.current_zone]
        nz    = len(self.sorted_worlds)

        # Zone header with directional arrows
        prefix = "← " if self.current_zone > 0 else "   "
        suffix = " →" if self.current_zone < nz - 1 else "   "
        self._t(f"{prefix}Zone {world}{suffix}",
                LEFT_W // 2, ZONE_HDR_CY, ZONE_C, 13, ax="center", ay="center")

        # Horizontal rule under header
        rule_y = WINDOW_HEIGHT - HDIVIDE_Y
        arcade.draw_line(0, rule_y, LEFT_W, rule_y, DIV_C, 1)

        # Level list
        for slot, idx in enumerate(self.world_indices[world]):
            item_top = LIST_TOP + slot * ITEM_H   # top-down
            item_cy  = item_top + ITEM_H // 2     # top-down centre

            is_sel  = (idx == self.current_index)
            is_done = (self.levels[idx]["id"] in self.progress)

            # Selection highlight bar
            if is_sel:
                arcade.draw_lrbt_rectangle_filled(
                    0, LEFT_W,
                    WINDOW_HEIGHT - item_top - ITEM_H,  # screen bottom
                    WINDOW_HEIGHT - item_top,            # screen top
                    SEL_BG_C,
                )

            # Done checkmark
            x = LPAD
            if is_done:
                self._t("✓", x, item_cy, DONE_C, 12, ax="left", ay="center")
                x += 16

            # Level name
            color = SEL_TEXT_C if is_sel else TEXT_C
            size  = 13 if is_sel else 12
            self._t(self.levels[idx]["name"], x, item_cy,
                    color, size, ax="left", ay="center")

    def _draw_preview(self):
        level = self.levels[self.current_index]
        state = self._states.get(level["id"])
        if state is None:
            return

        # Use the same cell_size as the real game's _scaled_cell_size(scale=1.0)
        cell_sz = GAME_GRID_PX // state.grid_size
        grid_px = cell_sz * state.grid_size   # may be < GAME_GRID_PX for non-6 grids

        self.renderer.draw_preview(state, GAME_X, GAME_Y, cell_sz)

        # Level id + name label — centred in the gap between grid bottom and footer
        grid_bottom_td = GAME_Y + grid_px          # e.g. 120+480 = 600
        label_td_y = (grid_bottom_td + FOOTER_CY) // 2  # midpoint of gap ≈ 653
        self._t(f"{level['id']}  {level['name']}",
                GAME_X + grid_px // 2, label_td_y,
                TEXT_C, 14, ax="center", ay="center")

    # ── Text helper ───────────────────────────────────────────────────────────

    def _t(self, text, x, td_y, color, size,
           ax="left", ay="baseline", bold=False):
        """Draw text.  td_y is top-down y (0 = top of window)."""
        screen_y = WINDOW_HEIGHT - td_y
        key = f"{text}|{size}|{bold}|{ax}|{ay}"
        if key not in self._text_cache:
            self._text_cache[key] = arcade.Text(
                text, x, screen_y, color, size,
                anchor_x=ax, anchor_y=ay,
                font_name="Microsoft YaHei", bold=bold,
            )
        else:
            t = self._text_cache[key]
            t.x = x
            t.y = screen_y
            t.color = color
        self._text_cache[key].draw()

    # ── Input ─────────────────────────────────────────────────────────────────

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.exit()
        elif key in (arcade.key.LEFT, arcade.key.A):
            self._switch_zone(-1)
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self._switch_zone(1)
        elif key == arcade.key.TAB:
            delta = -1 if (modifiers & arcade.key.MOD_SHIFT) else 1
            self._switch_zone(delta)
        elif key in (arcade.key.UP, arcade.key.W):
            self._move_cursor(-1)
        elif key in (arcade.key.DOWN, arcade.key.S):
            self._move_cursor(1)
        elif key in (arcade.key.ENTER, arcade.key.SPACE):
            self._launch()

    def _switch_zone(self, delta: int):
        self.current_zone = (self.current_zone + delta) % len(self.sorted_worlds)
        # Move cursor to first level of the new zone
        self.current_index = self.world_indices[self.sorted_worlds[self.current_zone]][0]

    def _move_cursor(self, delta: int):
        indices = self.world_indices[self.sorted_worlds[self.current_zone]]
        if self.current_index not in indices:
            self.current_index = indices[0]
            return
        pos = indices.index(self.current_index)
        self.current_index = indices[(pos + delta) % len(indices)]

    def _launch(self):
        from game_window import GameView
        from main import EMPTY_HINTS
        level    = self.levels[self.current_index]
        level_id = level["id"]
        game_view = GameView(
            level["floor_map"],
            level["object_map"],
            hints=level.get("hints") or EMPTY_HINTS.copy(),
            objective=level.get("objective"),
            first_time=level_id not in self.progress,
            cursor_index=self.current_index,
            all_levels=self.levels,
            progress=self.progress,
            level_id=level_id,
            player_facing=level.get("player_facing"),
        )
        self.window.show_view(game_view)
