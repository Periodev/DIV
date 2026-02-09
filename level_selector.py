# level_selector.py - Graphical Level Selector
#
# Arcade-based level selector with keyboard navigation

import arcade
from main import TUTORIAL_LEVELS, MAIN_LEVELS, load_progress, launch

# Window settings
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 700
BACKGROUND_COLOR = (20, 20, 25)

# Colors
TEXT_COLOR = (220, 220, 220)
TITLE_COLOR = (96, 165, 250)
HIGHLIGHT_COLOR = (96, 165, 250)
HIGHLIGHT_BG = (40, 80, 120)
SECTION_COLOR = (150, 150, 150)
PLAYED_COLOR = (80, 200, 120)

# Layout
TITLE_Y = 650
SECTION_START_Y = 580
LINE_HEIGHT = 35
INDENT = 100


class LevelSelectorWindow(arcade.Window):
    """Graphical level selector window."""

    def __init__(self):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, "DIV - Level Selector")

        # Build level list
        self.levels = TUTORIAL_LEVELS + MAIN_LEVELS
        self.current_index = 0

        # Load progress
        self.progress = load_progress()
        self.played_set = set(self.progress['played'])

        # Text cache
        self.text_cache = {}

        arcade.set_background_color(BACKGROUND_COLOR)

    def on_draw(self):
        """Render the level selector."""
        self.clear()

        # Title
        self._draw_text("DIV - Timeline Puzzle", WINDOW_WIDTH // 2, TITLE_Y,
                       TITLE_COLOR, 32, anchor_x="center", bold=True)
        self._draw_text("選擇關卡", WINDOW_WIDTH // 2, TITLE_Y - 35,
                       TEXT_COLOR, 18, anchor_x="center")

        # Instructions
        self._draw_text("↑↓ 選擇  |  ENTER/SPACE 開始  |  ESC 退出",
                       WINDOW_WIDTH // 2, 30, SECTION_COLOR, 14, anchor_x="center")

        # Draw level list
        y = SECTION_START_Y

        # World 0
        self._draw_text("World 0 - 基礎機制", 50, y, SECTION_COLOR, 16, bold=True)
        y -= LINE_HEIGHT
        for i in range(6):
            y = self._draw_level_item(i, y)

        y -= 20
        # World 1
        self._draw_text("World 1 - 時間線機制", 50, y, SECTION_COLOR, 16, bold=True)
        y -= LINE_HEIGHT
        for i in range(6, 11):
            y = self._draw_level_item(i, y)

        y -= 20
        # World 2
        self._draw_text("World 2 - 進階機制", 50, y, SECTION_COLOR, 16, bold=True)
        y -= LINE_HEIGHT
        for i in range(11, len(self.levels)):
            y = self._draw_level_item(i, y)

    def _draw_level_item(self, index, y):
        """Draw a single level item."""
        level = self.levels[index]
        is_current = (index == self.current_index)
        is_played = level['id'] in self.played_set

        # Highlight background for current selection
        if is_current:
            left = 40
            right = WINDOW_WIDTH - 40
            bottom = y - (LINE_HEIGHT - 5) // 2
            top = y + (LINE_HEIGHT - 5) // 2
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, HIGHLIGHT_BG)

        # Played marker
        marker = "✓" if is_played else " "
        marker_color = PLAYED_COLOR if is_played else TEXT_COLOR
        self._draw_text(marker, INDENT - 30, y, marker_color, 20, anchor_y="center")

        # Level info
        text = f"{level['id']}  {level['name']}"
        color = HIGHLIGHT_COLOR if is_current else TEXT_COLOR
        font_size = 16 if is_current else 14
        self._draw_text(text, INDENT, y, color, font_size, anchor_y="center")

        return y - LINE_HEIGHT

    def _draw_text(self, text, x, y, color, size, anchor_x="left", anchor_y="baseline", bold=False):
        """Draw text with caching."""
        cache_key = f"{text}_{size}_{bold}"

        if cache_key not in self.text_cache:
            self.text_cache[cache_key] = arcade.Text(
                text, x, y, color, size,
                anchor_x=anchor_x, anchor_y=anchor_y,
                font_name="Arial" if not bold else "Arial",
                bold=bold
            )
        else:
            cached = self.text_cache[cache_key]
            cached.x = x
            cached.y = y
            cached.color = color

        self.text_cache[cache_key].draw()

    def on_key_press(self, key, modifiers):
        """Handle keyboard input."""
        if key == arcade.key.ESCAPE:
            # Exit selector
            arcade.exit()

        elif key == arcade.key.UP:
            # Move selection up
            self.current_index = (self.current_index - 1) % len(self.levels)

        elif key == arcade.key.DOWN:
            # Move selection down
            self.current_index = (self.current_index + 1) % len(self.levels)

        elif key in (arcade.key.ENTER, arcade.key.SPACE):
            # Launch selected level
            selected_level = self.levels[self.current_index]
            self.close()
            launch(selected_level)


def run_level_selector():
    """Run the graphical level selector."""
    window = LevelSelectorWindow()
    arcade.run()


if __name__ == "__main__":
    run_level_selector()
