# game_window.py - Arcade Game View
#
# Game view (arcade.View) with rendering and input handling.
# Handles slide animations for timeline focus switching.

import time
import arcade
from map_parser import parse_dual_layer
from game_controller import GameController
from presentation_model import ViewModelBuilder
from render_arc import ArcadeRenderer, WINDOW_WIDTH, WINDOW_HEIGHT
from timeline_system import EntityType, Physics


class GameView(arcade.View):
    """Main game view using Arcade."""

    # Animation settings
    SLIDE_DURATION = 0.25  # seconds for slide animation

    def __init__(self, floor_map: str, object_map: str, hints: dict = None,
                 objective: dict = None, first_time: bool = False,
                 cursor_index: int = 0, all_levels: list = None,
                 progress: set = None, level_id: str = None,
                 player_facing: str = None):
        super().__init__()

        # Parse map and create controller
        source = parse_dual_layer(floor_map, object_map, player_facing=player_facing)
        self._source = source
        self.controller = GameController(source)
        self._set_initial_facing(source)

        # Renderer
        self.renderer = ArcadeRenderer()
        self.renderer.set_grid_size(source.grid_size)

        # Hint configuration (tutorial progression)
        self.hints = hints or {
            'pickup': True,
            'diverge': True,
            'converge': True,
            'fetch': True,
        }

        # Objective overlay state (ESC key — level name + task description)
        self.objective = objective  # {'title': str, 'items': [str, ...]}
        # Auto-show objective on first-time entry
        self.show_objective = first_time and objective is not None

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

        # Track held keys for continuous movement
        self.held_keys = set()
        self.alt_held = False
        self.ctrl_held = False
        self.c_held = False  # C key: peek floor

        # Menu navigation context (for returning to menu)
        self.cursor_index = cursor_index
        self.all_levels = all_levels or []
        self.progress = progress if progress is not None else set()
        self.level_id = level_id

    def on_show_view(self):
        arcade.set_background_color((20, 20, 25))
        self.window.set_update_rate(1 / 60)

    def on_update(self, delta_time: float):
        """Called every frame for game logic updates."""
        self.animation_frame += 1

        if self.move_cooldown > 0:
            self.move_cooldown -= 1

        # Slide animation completion
        if self.slide_start_time is not None:
            elapsed = time.time() - self.slide_start_time
            if elapsed >= self.SLIDE_DURATION:
                # Animation complete - commit the focus change via controller
                self.controller.switch_focus()
                self.slide_start_time = None
                self.slide_direction = 0

        # Merge preview swap animation completion
        if self.merge_preview_swap_start_time is not None:
            elapsed = time.time() - self.merge_preview_swap_start_time
            if elapsed >= self.MERGE_PREVIEW_SWAP_DURATION:
                # Animation complete - commit focus switch via controller
                self.controller.switch_focus()
                self.merge_preview_swap_start_time = None

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
        # ESC — close overlay first; if no overlay, return to menu
        if key == arcade.key.ESCAPE:
            if self.show_objective:
                self.show_objective = False
                return
            self._return_to_menu()
            return

        # F1 — toggle level-info overlay
        if key == arcade.key.F1:
            if self.objective:
                self.show_objective = not self.show_objective
            return

        # Enter / Space — also close level-info overlay
        if key in (arcade.key.ENTER, arcade.key.SPACE) and self.show_objective:
            self.show_objective = False
            return

        # Block game input when level-info overlay is shown
        if self.show_objective:
            return

        if key in (arcade.key.LALT, arcade.key.RALT):
            self.alt_held = True
            return
        if key in (arcade.key.LCTRL, arcade.key.RCTRL):
            self.ctrl_held = True  # Only active in M preview mode (fetch lines)
            return
        if key == arcade.key.C:
            self.c_held = True    # Peek floor
            return
        # Movement keys - add to held set
        if key in (arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT,
                   arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D):
            self.held_keys.add(key)
            return

        # Reset
        if key == arcade.key.F5 or key == arcade.key.R:
            self.controller.reset()
            self._set_initial_facing(self._source)
            self.slide_start_time = None
            self.slide_direction = 0
            self.merge_preview_active = False
            self.merge_preview_start_time = None
            return

        # Undo
        if key == arcade.key.Z:
            self.controller.undo()
            return

        # Return to menu on victory (SPACE key)
        if self.controller.victory and key == arcade.key.SPACE:
            if self.level_id:
                from main import mark_as_played
                mark_as_played(self.level_id)
                self.progress.add(self.level_id)
            self._return_to_menu()
            return

        # Skip actions if collapsed or victory
        if self.controller.collapsed or self.controller.victory:
            return

        # Fetch merge (F key — direct action, no toggle)
        if key == arcade.key.F:
            if self.controller.has_branched and self.hints.get('fetch', True):
                self.controller.try_fetch_merge()
            return

        # Branch / Merge (V key)
        if key == arcade.key.V:
            if self.controller.has_branched:
                self.controller.try_merge()
            else:
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
            self.controller.handle_adaptive_action(
                allow_converge=self.hints.get('converge', True),
                allow_pickup=self.hints.get('pickup', True)
            )

    def on_key_release(self, key: int, modifiers: int):
        """Handle key release events."""
        if key in (arcade.key.LALT, arcade.key.RALT):
            self.alt_held = False
            return
        if key in (arcade.key.LCTRL, arcade.key.RCTRL):
            self.ctrl_held = False
            return
        if key == arcade.key.C:
            self.c_held = False
            return
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

        # Build frame spec from controller state
        frame_spec = ViewModelBuilder.build(
            self.controller,
            self.animation_frame,
            slide_progress,
            self.slide_direction,
            self.merge_preview_active,
            self.merge_preview_active and self.ctrl_held and self.controller.can_show_fetch_hint(),
            merge_preview_progress,
            merge_preview_swap_progress,
            self.controller.can_show_fetch_hint(),  # capability indicator (not a mode toggle)
            self.hints
        )

        # Render
        self.renderer.peek_floor_mode = self.c_held
        self.renderer.draw_frame(frame_spec)

        # Draw objective overlay if active (F1 key)
        if self.show_objective and self.objective:
            self.renderer._draw_tutorial(self.objective, close_hint='ESC / Enter / Space 關閉')

    def _set_initial_facing(self, source):
        """Set player's initial facing direction.

        If the level specifies player_facing in metadata, that takes priority.
        Otherwise, fall back to facing toward the nearest grounded box.
        """
        if source.player_facing is not None:
            return  # already applied in init_branch_from_source()

        branch = self.controller.main_branch
        player = branch.player
        boxes = [e for e in branch.entities
                 if e.uid != 0 and e.type == EntityType.BOX and Physics.grounded(e)]
        if not boxes:
            return
        px, py = player.pos
        nearest = min(boxes, key=lambda e: abs(e.pos[0] - px) + abs(e.pos[1] - py))
        dx = nearest.pos[0] - px
        dy = nearest.pos[1] - py
        if abs(dx) >= abs(dy):
            player.direction = (1 if dx > 0 else -1, 0)
        else:
            player.direction = (0, 1 if dy > 0 else -1)

    def _return_to_menu(self):
        """Switch back to MenuView, preserving cursor position."""
        from menu_view import MenuView
        menu_view = MenuView(self.all_levels, self.progress, self.cursor_index)
        self.window.show_view(menu_view)

