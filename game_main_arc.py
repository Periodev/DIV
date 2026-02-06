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

        # Slide animation state
        self.slide_start_time = None
        self.slide_direction = 0  # 1 = switching to DIV1, -1 = switching to DIV0

        # Merge preview state
        self.merge_preview_active = False
        self.merge_preview_start_time = None
        self.MERGE_PREVIEW_DURATION = 0.3  # seconds for preview animation

        # Merge preview swap animation (Tab in preview mode)
        self.merge_preview_swap_start_time = None
        self.MERGE_PREVIEW_SWAP_DURATION = 0.25  # seconds for swap animation

        # Merge animation (C key confirms merge)
        self.merge_animation_start_time = None
        self.MERGE_ANIMATION_DURATION = 0.3  # seconds for merge animation
        self.merge_animation_pre_focus = None  # Store focus before merge for animation
        self.merge_animation_stored_main = None  # Store main_branch state for animation
        self.merge_animation_stored_sub = None   # Store sub_branch state for animation

        # Track held keys for continuous movement
        self.held_keys = set()

        arcade.set_background_color(arcade.color.WHITE)

    def on_update(self, delta_time: float):
        """Called every frame for game logic updates."""
        self.animation_frame += 1

        if self.move_cooldown > 0:
            self.move_cooldown -= 1

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

        # Merge preview swap animation completion
        if self.merge_preview_swap_start_time is not None:
            elapsed = time.time() - self.merge_preview_swap_start_time
            if elapsed >= self.MERGE_PREVIEW_SWAP_DURATION:
                # Animation complete - commit focus switch
                self.controller.current_focus = 1 - self.controller.current_focus
                self.merge_preview_swap_start_time = None

        # Merge animation completion
        if self.merge_animation_start_time is not None:
            elapsed = time.time() - self.merge_animation_start_time
            if elapsed >= self.MERGE_ANIMATION_DURATION:
                # Animation complete - merge already executed, just clean up
                self.merge_preview_active = False
                self.merge_preview_start_time = None
                self.merge_animation_start_time = None
                self.merge_animation_pre_focus = None
                self.merge_animation_stored_main = None
                self.merge_animation_stored_sub = None

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
            self.merge_preview_active = False
            self.merge_preview_start_time = None
            return

        # Undo
        if key == arcade.key.Z:
            self.controller.undo()
            return

        # Skip actions if collapsed or victory
        if self.controller.collapsed or self.controller.victory:
            return

        # Branch (V key)
        # Branch (V key)
        if key == arcade.key.V:
            if not self.controller.has_branched:
                self.controller.try_branch()
                # Clear any lingering merge preview state
                self.merge_preview_active = False
                self.merge_preview_start_time = None

        # Merge preview toggle (M key)
        elif key == arcade.key.M:
            if self.controller.has_branched:
                if self.merge_preview_active:
                    # Cancel preview
                    self.merge_preview_active = False
                    self.merge_preview_start_time = None
                else:
                    # Enter preview
                    self.merge_preview_active = True
                    self.merge_preview_start_time = time.time()

        # Cancel merge preview (Esc)
        elif key == arcade.key.ESCAPE:
            if self.merge_preview_active:
                self.merge_preview_active = False
                self.merge_preview_start_time = None

        # Merge confirm (C key) - works in preview or directly
        elif key == arcade.key.C:
            if self.controller.has_branched:
                if self.merge_preview_active:
                    # In preview mode: store states, execute merge, then animate
                    self.merge_animation_pre_focus = self.controller.current_focus
                    self.merge_animation_stored_main = self.controller.main_branch
                    self.merge_animation_stored_sub = self.controller.sub_branch
                    self.controller.try_merge()  # Execute immediately
                    self.merge_animation_start_time = time.time()  # Then animate with stored states
                else:
                    # Not in preview: merge directly
                    self.controller.try_merge()

        # Switch focus with slide animation (Tab)
        elif key == arcade.key.TAB:
            if self.controller.has_branched:
                if self.merge_preview_active:
                    # In merge preview: start swap animation if not already swapping
                    if self.merge_preview_swap_start_time is None:
                        self.merge_preview_swap_start_time = time.time()
                elif self.slide_start_time is None:
                    # Normal mode: start slide animation
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

    def on_draw(self):
        """Render the game."""
        self.clear()

        # Calculate slide animation progress
        slide_progress = 0.0
        if self.slide_start_time is not None:
            elapsed = time.time() - self.slide_start_time
            slide_progress = min(elapsed / self.SLIDE_DURATION, 1.0)

        # Calculate merge preview animation progress
        merge_preview_progress = 0.0
        if self.merge_preview_start_time is not None:
            elapsed = time.time() - self.merge_preview_start_time
            merge_preview_progress = min(elapsed / self.MERGE_PREVIEW_DURATION, 1.0)

        # Calculate merge preview swap progress
        merge_preview_swap_progress = 0.0
        if self.merge_preview_swap_start_time is not None:
            elapsed = time.time() - self.merge_preview_swap_start_time
            merge_preview_swap_progress = min(elapsed / self.MERGE_PREVIEW_SWAP_DURATION, 1.0)

        # Calculate merge animation progress
        merge_animation_progress = 0.0
        if self.merge_animation_start_time is not None:
            elapsed = time.time() - self.merge_animation_start_time
            merge_animation_progress = min(elapsed / self.MERGE_ANIMATION_DURATION, 1.0)

        # Build frame spec from controller state
        frame_spec = ViewModelBuilder.build(
            self.controller,
            self.animation_frame,
            slide_progress,
            self.slide_direction,
            self.merge_preview_active,
            merge_preview_progress,
            merge_preview_swap_progress,
            merge_animation_progress,
            self.merge_animation_pre_focus,
            self.merge_animation_stored_main,
            self.merge_animation_stored_sub
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
