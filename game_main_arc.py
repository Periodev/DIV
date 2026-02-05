# game_main_arc.py - Arcade Main Loop
#
# Arcade-based game window with slide animation for focus switching.

import time
import arcade
from map_parser import parse_dual_layer
from game_controller import GameController
from presentation_model import ViewModelBuilder
from render_arc import ArcadeRenderer, WINDOW_WIDTH, WINDOW_HEIGHT


class GameWindow(arcade.Window):
    """Main game window using Arcade."""

    # Animation settings
    SLIDE_DURATION = 0.25  # seconds for slide animation

    def __init__(self, floor_map: str, object_map: str):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, "div - Timeline Puzzle")

        self.set_update_rate(1/60)  # 60 FPS

        # Parse map and create controller
        source = parse_dual_layer(floor_map, object_map)
        self.controller = GameController(source)

        # Renderer
        self.renderer = ArcadeRenderer()

        # Input state
        self.move_cooldown = 0
        self.MOVE_DELAY = 10
        self.animation_frame = 0

        # V-key hold state
        self.v_press_time = None
        self.V_HOLD_THRESHOLD = 0.8  # seconds

        # Slide animation state
        self.slide_start_time = None
        self.slide_direction = 0  # 1 = switching to DIV1, -1 = switching to DIV0

        # Track held keys for continuous movement
        self.held_keys = set()

        arcade.set_background_color(arcade.color.WHITE)

    def on_update(self, delta_time: float):
        """Called every frame for game logic updates."""
        self.animation_frame += 1

        if self.move_cooldown > 0:
            self.move_cooldown -= 1

        # V-key hold merge
        if self.v_press_time is not None and self.controller.has_branched:
            if not self.controller.collapsed and not self.controller.victory:
                hold_duration = time.time() - self.v_press_time
                if hold_duration >= self.V_HOLD_THRESHOLD:
                    self.controller.try_merge()
                    self.v_press_time = None

        # Slide animation completion
        if self.slide_start_time is not None:
            elapsed = time.time() - self.slide_start_time
            if elapsed >= self.SLIDE_DURATION:
                # Animation complete - commit the focus change
                if self.slide_direction == 1:
                    self.controller.current_focus = 1
                else:
                    self.controller.current_focus = 0
                self.slide_start_time = None
                self.slide_direction = 0

        # Continuous movement from held keys (only if not animating)
        if not self.controller.collapsed and not self.controller.victory:
            if self.slide_start_time is None and self.move_cooldown == 0:
                direction = self._get_movement_direction()
                if direction:
                    self.controller.handle_move(direction)
                    self.move_cooldown = self.MOVE_DELAY

        # Physics update
        if not self.controller.collapsed and not self.controller.victory:
            self.controller.update_physics()

        # Victory check
        if not self.controller.victory and self.controller.check_victory():
            solution = ''.join(self.controller.input_log)
            print(f"\n=== VICTORY ===")
            print(f"Steps: {len(self.controller.input_log)}")
            print(f"Solution: {solution}")
            print(f"===============\n")

    def _get_movement_direction(self):
        """Get movement direction from held keys."""
        if arcade.key.UP in self.held_keys or arcade.key.W in self.held_keys:
            return (0, -1)
        elif arcade.key.DOWN in self.held_keys or arcade.key.S in self.held_keys:
            return (0, 1)
        elif arcade.key.LEFT in self.held_keys or arcade.key.A in self.held_keys:
            return (-1, 0)
        elif arcade.key.RIGHT in self.held_keys or arcade.key.D in self.held_keys:
            return (1, 0)
        return None

    def on_key_press(self, key: int, modifiers: int):
        """Handle key press events."""
        # Movement keys - add to held set
        if key in (arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT,
                   arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D):
            self.held_keys.add(key)
            return

        # Reset
        if key == arcade.key.F5 or key == arcade.key.R:
            self.controller.reset()
            self.slide_start_time = None
            self.slide_direction = 0
            return

        # Undo
        if key == arcade.key.Z:
            self.controller.undo()
            return

        # Skip actions if collapsed or victory
        if self.controller.collapsed or self.controller.victory:
            return

        # Branch (V key)
        if key == arcade.key.V:
            if not self.controller.has_branched:
                self.controller.try_branch()
            else:
                self.v_press_time = time.time()

        # Merge (C key)
        elif key == arcade.key.C:
            self.controller.try_merge()

        # Switch focus with slide animation (Tab)
        elif key == arcade.key.TAB:
            if self.controller.has_branched and self.slide_start_time is None:
                # Start slide animation
                self.slide_start_time = time.time()
                if self.controller.current_focus == 0:
                    self.slide_direction = 1  # Moving to DIV1
                else:
                    self.slide_direction = -1  # Moving to DIV0

        # Adaptive action (X or Space)
        elif key == arcade.key.X or key == arcade.key.SPACE:
            self.controller.handle_adaptive_action()

    def on_key_release(self, key: int, modifiers: int):
        """Handle key release events."""
        if key in self.held_keys:
            self.held_keys.discard(key)

        if key == arcade.key.V:
            self.v_press_time = None

    def on_draw(self):
        """Render the game."""
        self.clear()

        # Calculate V-key hold progress
        v_hold_progress = 0.0
        if self.v_press_time is not None and self.controller.has_branched:
            elapsed = time.time() - self.v_press_time
            v_hold_progress = min(elapsed / self.V_HOLD_THRESHOLD, 1.0)

        # Calculate slide animation progress
        slide_progress = 0.0
        if self.slide_start_time is not None:
            elapsed = time.time() - self.slide_start_time
            slide_progress = min(elapsed / self.SLIDE_DURATION, 1.0)

        # Build frame spec from controller state
        frame_spec = ViewModelBuilder.build(
            self.controller,
            self.animation_frame,
            v_hold_progress,
            slide_progress,
            self.slide_direction
        )

        # Render
        self.renderer.draw_frame(frame_spec)


def run_game(floor_map: str, object_map: str):
    """Main entry point - creates window and runs game loop."""
    window = GameWindow(floor_map, object_map)
    arcade.run()


# ===== Map Definition =====
floor_map = '''
#.V.S#
#H.#.#
#H##H#
#HG#H#
###.H#
#..V.#
'''

object_map = '''
.B....
......
......
......
......
.BP.B.
'''


if __name__ == "__main__":
    run_game(floor_map, object_map)
