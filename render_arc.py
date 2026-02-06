# render_arc.py - Arcade Rendering System (Layer 3)
#
# Arcade-based renderer. Receives visual specifications from presentation_model
# and draws using arcade's optimized rendering pipeline.

import math
import time
import arcade
from typing import Optional, Tuple, List, TYPE_CHECKING
from timeline_system import BranchState, TerrainType, EntityType

if TYPE_CHECKING:
    from presentation_model import FrameViewSpec, BranchViewSpec, InteractionHint

# === Layout Constants ===
GRID_SIZE = 6
CELL_SIZE = 75
GRID_WIDTH = GRID_SIZE * CELL_SIZE  # 450
GRID_HEIGHT = GRID_SIZE * CELL_SIZE

WINDOW_WIDTH = 1150
WINDOW_HEIGHT = 600
PADDING = 30

# === Colors (RGBA for arcade) ===
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
BLUE = (0, 100, 200)
GREEN = (50, 150, 50)
DARK_GRAY = (100, 100, 100)
YELLOW = (255, 200, 0)
ORANGE = (255, 150, 50)
LIGHT_ORANGE = (255, 200, 150)
CYAN = (0, 220, 220)

# Box colors (colorblind-friendly)
BOX_COLORS = [
    (230, 80, 80),    # Red
    (70, 130, 180),   # Steel Blue
    (255, 180, 0),    # Orange
]

# Hint panel colors
HINT_BG = (40, 40, 40)
HINT_TEXT_GRAY = (200, 200, 200)


def desaturate_color(color: Tuple[int, int, int], amount: float = 0.5) -> Tuple[int, int, int]:
    """Desaturate a color by blending towards gray."""
    r, g, b = color[:3]
    gray = (r + g + b) / 3
    return (
        int(r + (gray - r) * amount),
        int(g + (gray - g) * amount),
        int(b + (gray - b) * amount)
    )


class ArcadeRenderer:
    """Arcade-based renderer for the game."""

    def __init__(self):
        # Text objects (cached for performance)
        self.debug_text: Optional[arcade.Text] = None

        # Font path for Chinese characters
        self.chinese_font = "Microsoft YaHei"

        # === Texture Cache for SpriteList Rendering ===
        self._init_texture_cache()

    def _init_texture_cache(self):
        """Initialize cached textures for GPU-batched rendering."""
        # Terrain textures at base cell size
        self._terrain_textures = {
            'white': arcade.make_soft_square_texture(CELL_SIZE, WHITE, outer_alpha=255),
            'black': arcade.make_soft_square_texture(CELL_SIZE, BLACK, outer_alpha=255),
            'gray': arcade.make_soft_square_texture(CELL_SIZE, GRAY, outer_alpha=255),
            'yellow': arcade.make_soft_square_texture(CELL_SIZE, YELLOW, outer_alpha=255),
            'light_orange': arcade.make_soft_square_texture(CELL_SIZE, LIGHT_ORANGE, outer_alpha=255),
            'no_carry_bg': arcade.make_soft_square_texture(CELL_SIZE, (255, 240, 220), outer_alpha=255),
            'switch_on': arcade.make_soft_square_texture(CELL_SIZE, (200, 255, 200), outer_alpha=255),
            'switch_off': arcade.make_soft_square_texture(CELL_SIZE, (255, 200, 200), outer_alpha=255),
            'hole_filled': arcade.make_soft_square_texture(CELL_SIZE, (160, 120, 60), outer_alpha=255),
            'hole_empty': arcade.make_soft_square_texture(CELL_SIZE, (60, 40, 20), outer_alpha=255),
            'branch_highlight': arcade.make_soft_square_texture(CELL_SIZE, (150, 255, 150), outer_alpha=255),
        }

        # Box textures (one per color)
        box_size = int(CELL_SIZE * 0.8)  # Box is smaller than cell
        self._box_textures = [
            arcade.make_soft_square_texture(box_size, color, outer_alpha=255)
            for color in BOX_COLORS
        ]
        self._box_textures_desaturated = [
            arcade.make_soft_square_texture(box_size, desaturate_color(color, 0.5), outer_alpha=255)
            for color in BOX_COLORS
        ]

        # Player textures
        player_radius = CELL_SIZE // 5
        self._player_texture = arcade.make_circle_texture(player_radius * 2, BLUE)
        self._player_texture_gray = arcade.make_circle_texture(player_radius * 2, GRAY)

        # Scaled texture cache (lazy-loaded)
        self._scaled_textures: dict = {}

        # Text object cache for GPU-efficient text rendering
        self._text_cache: dict = {}

        # Pre-create static text objects
        self._init_static_text()

    def _init_static_text(self):
        """Pre-create commonly used static text objects."""
        # Overlay text (centered, sized for 800x600 window)
        self._overlay_texts = {
            'fall': arcade.Text("FALL DOWN!", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40,
                               YELLOW, font_size=48, anchor_x="center", anchor_y="center"),
            'victory': arcade.Text("LEVEL COMPLETE!", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40,
                                  YELLOW, font_size=36, anchor_x="center", anchor_y="center"),
            'hint': arcade.Text("F5 restart Z undo", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20,
                               WHITE, font_size=14, anchor_x="center", anchor_y="center"),
        }

        # Merge progress labels
        self._merge_labels = {
            'merging': arcade.Text("... Merge", 0, 0, (150, 50, 150), font_size=14,
                                   anchor_x="left", anchor_y="center"),
            'ready': arcade.Text("合併", 0, 0, (150, 50, 150), font_size=14,
                                anchor_x="left", anchor_y="center"),
        }

        # Debug text (single object, content updated each frame)
        self._debug_text = arcade.Text("", PADDING, 0, DARK_GRAY, font_size=14,
                                       anchor_x="left", anchor_y="center")

    def _get_text(self, key: str, text: str, x: int, y: int, color: tuple,
                  font_size: int = 14, anchor_x: str = "center", anchor_y: str = "center") -> arcade.Text:
        """Get or create a cached text object."""
        cache_key = (key, text, font_size, color, anchor_x, anchor_y)
        if cache_key not in self._text_cache:
            self._text_cache[cache_key] = arcade.Text(
                text, x, y, color, font_size=font_size,
                anchor_x=anchor_x, anchor_y=anchor_y
            )
        text_obj = self._text_cache[cache_key]
        # Update position (text content is cached, position may vary)
        text_obj.x = x
        text_obj.y = y
        return text_obj

    def _draw_cached_text(self, key: str, text: str, x: int, y: int, color: tuple,
                          font_size: int = 14, anchor_x: str = "center", anchor_y: str = "center"):
        """Draw text using cache for better performance."""
        text_obj = self._get_text(key, text, x, y, color, font_size, anchor_x, anchor_y)
        text_obj.draw()

    def _get_scaled_texture(self, base_key: str, scale: float) -> arcade.Texture:
        """Get or create a scaled version of a base texture."""
        cache_key = (base_key, scale)
        if cache_key not in self._scaled_textures:
            base_texture = self._terrain_textures[base_key]
            if scale == 1.0:
                self._scaled_textures[cache_key] = base_texture
            else:
                # Create scaled texture
                new_size = int(CELL_SIZE * scale)
                color_map = {
                    'white': WHITE, 'black': BLACK, 'gray': GRAY,
                    'yellow': YELLOW, 'light_orange': LIGHT_ORANGE,
                    'no_carry_bg': (255, 240, 220),
                    'switch_on': (200, 255, 200), 'switch_off': (255, 200, 200),
                    'hole_filled': (160, 120, 60), 'hole_empty': (60, 40, 20),
                    'branch_highlight': (150, 255, 150),
                }
                self._scaled_textures[cache_key] = arcade.make_soft_square_texture(
                    new_size, color_map[base_key], outer_alpha=255
                )
        return self._scaled_textures[cache_key]

    def _build_terrain_spritelist(self, state: BranchState, start_x: int, start_y: int,
                                   cell_size: int, goal_active: bool, has_branched: bool,
                                   highlight_branch_point: bool,
                                   terrain_diff_reference: Optional[BranchState] = None) -> tuple:
        """Build SpriteList for static terrain. Returns (spritelist, dynamic_cells).

        dynamic_cells contains positions that need immediate-mode rendering (Goal, highlighted branch).

        Args:
            terrain_diff_reference: If provided, only include cells where terrain differs from reference.
        """
        scale = cell_size / CELL_SIZE
        sprites = arcade.SpriteList()
        dynamic_cells = []  # (gx, gy, terrain_type) for immediate mode

        for gx in range(GRID_SIZE):
            for gy in range(GRID_SIZE):
                pos = (gx, gy)
                terrain = state.terrain.get(pos, TerrainType.FLOOR)
                center_x = start_x + gx * cell_size + cell_size // 2
                center_y = self._flip_y(start_y + gy * cell_size + cell_size // 2)

                # Filter: only draw cells that differ from reference (if provided)
                if terrain_diff_reference is not None:
                    ref_terrain = terrain_diff_reference.terrain.get(pos, TerrainType.FLOOR)

                    # Check if terrain differs
                    if terrain != ref_terrain:
                        pass  # Different terrain type - include this cell
                    elif terrain == TerrainType.SWITCH:
                        # Check if switch activation state differs
                        activated = state.switch_activated(pos)
                        ref_activated = terrain_diff_reference.switch_activated(pos)
                        if activated == ref_activated:
                            continue  # Same activation state - skip
                    elif terrain == TerrainType.HOLE:
                        # Check if hole filled state differs
                        filled = state.is_hole_filled(pos)
                        ref_filled = terrain_diff_reference.is_hole_filled(pos)
                        if filled == ref_filled:
                            continue  # Same filled state - skip
                    else:
                        continue  # Same terrain, no state difference - skip

                # Determine texture key
                texture_key = None

                if terrain == TerrainType.WALL:
                    texture_key = 'black'
                elif terrain == TerrainType.SWITCH:
                    activated = state.switch_activated(pos)
                    texture_key = 'switch_on' if activated else 'switch_off'
                elif terrain == TerrainType.NO_CARRY:
                    texture_key = 'no_carry_bg'
                    dynamic_cells.append((gx, gy, terrain, False))  # Need NO_CARRY rendering
                elif terrain in (TerrainType.BRANCH1, TerrainType.BRANCH2,
                                TerrainType.BRANCH3, TerrainType.BRANCH4):
                    # Check if this is a highlighted branch point
                    if (highlight_branch_point and pos == state.player.pos):
                        texture_key = 'branch_highlight'
                        dynamic_cells.append((gx, gy, terrain, True))  # True = highlighted
                    else:
                        texture_key = 'white'
                        dynamic_cells.append((gx, gy, terrain, False))  # Need branch marker
                elif terrain == TerrainType.GOAL:
                    # Goal is always dynamic (flash effect)
                    dynamic_cells.append((gx, gy, terrain, goal_active))
                    texture_key = None  # Will be drawn in immediate mode
                elif terrain == TerrainType.HOLE:
                    filled = state.is_hole_filled(pos)
                    texture_key = 'hole_filled' if filled else 'hole_empty'
                else:
                    texture_key = 'white'

                # Create sprite if static
                if texture_key:
                    texture = self._get_scaled_texture(texture_key, scale)
                    sprite = arcade.Sprite(texture)
                    sprite.center_x = center_x
                    sprite.center_y = center_y
                    sprites.append(sprite)

        return sprites, dynamic_cells

    def _draw_dynamic_terrain(self, start_x: int, start_y: int, state: BranchState,
                              cell_size: int, dynamic_cells: list, has_branched: bool, alpha: float = 1.0,
                              terrain_diff_reference: Optional[BranchState] = None):
        """Draw dynamic terrain elements (Goal flash, branch markers).

        Args:
            terrain_diff_reference: If provided, only draw cells where terrain differs from reference.
        """
        scale = cell_size / CELL_SIZE

        for gx, gy, terrain, extra in dynamic_cells:
            cell_x = start_x + gx * cell_size
            cell_y = start_y + gy * cell_size
            center_x, center_y = self._grid_to_screen(start_x, start_y, gx, gy, cell_size)

            if terrain == TerrainType.GOAL:
                goal_active = extra
                if goal_active:
                    flash = int((time.time() * 1000 / 300) % 2)
                    color = (255, 255, 100, int(alpha * 255)) if flash else (*YELLOW, int(alpha * 255))
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, color)
                    self._draw_rect_outline(cell_x, cell_y, cell_size, cell_size,
                                           (*GREEN, int(alpha * 255)), max(1, int(6 * scale)))
                else:
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, (*YELLOW, int(alpha * 255)))
                self._draw_cached_text(f'goal_{scale:.2f}_{alpha:.2f}', 'Goal', center_x, center_y,
                                       (*BLACK, int(alpha * 255)), font_size=int(14 * scale))

            elif terrain in (TerrainType.BRANCH1, TerrainType.BRANCH2,
                            TerrainType.BRANCH3, TerrainType.BRANCH4):
                is_highlighted = extra
                if is_highlighted:
                    self._draw_branch_marker(center_x, center_y, terrain, (*GREEN, int(alpha * 255)), cell_size)
                else:
                    color = (*GRAY, int(alpha * 255)) if has_branched else (*GREEN, int(alpha * 255))
                    self._draw_branch_marker(center_x, center_y, terrain, color, cell_size)

        # Draw NO_CARRY markers
        for gx in range(GRID_SIZE):
            for gy in range(GRID_SIZE):
                pos = (gx, gy)
                terrain = state.terrain.get(pos, TerrainType.FLOOR)

                # Filter: only draw cells that differ from reference (if provided)
                if terrain_diff_reference is not None:
                    ref_terrain = terrain_diff_reference.terrain.get(pos, TerrainType.FLOOR)
                    # Only check terrain type for these static decorations
                    if terrain == ref_terrain:
                        continue  # Same terrain - skip

                if terrain == TerrainType.NO_CARRY:
                    cell_x = start_x + gx * cell_size
                    cell_y = start_y + gy * cell_size
                    center_x, center_y = self._grid_to_screen(start_x, start_y, gx, gy, cell_size)
                    # Dark orange border
                    self._draw_rect_outline(cell_x, cell_y, cell_size, cell_size,
                                           (*((255, 140, 0)), int(alpha * 255)),
                                           max(1, int(4 * scale)))
                    # 'c' symbol
                    self._draw_cached_text(f'nocarry_{scale:.2f}_{alpha:.2f}', 'c',
                                           center_x, center_y, (*((255, 100, 0)), int(alpha * 255)),
                                           font_size=int(14 * scale))

    def draw_frame(self, spec: 'FrameViewSpec'):
        """Main entry point for rendering a complete frame.

        Layout: Single focused branch centered, other branch slides in/out
        """
        # 1. Clear screen
        arcade.draw_lrbt_rectangle_filled(
            0, WINDOW_WIDTH, 0, WINDOW_HEIGHT, WHITE
        )

        # 2. Draw branches
        # Merge preview mode: draw focused first (opaque), then non-focused on top (transparent)
        # Normal mode: draw non-focused first, then focused on top
        # Determine if in merge preview by checking if both branches are at similar positions with different alphas
        in_merge_preview = False
        if spec.sub_branch:
            # Check if both branches are centered (merge preview)
            both_centered = abs(spec.main_branch.pos_x - spec.sub_branch.pos_x) < 50
            has_transparency = spec.main_branch.alpha < 0.9 or spec.sub_branch.alpha < 0.9
            in_merge_preview = both_centered and has_transparency

        if in_merge_preview:
            # Merge preview: layered rendering for focused objects on top
            focused_branch = spec.main_branch if spec.current_focus == 0 else spec.sub_branch
            non_focused_branch = spec.sub_branch if spec.current_focus == 0 else spec.main_branch
            hidden_main = spec.main_branch.state
            hidden_sub = spec.sub_branch.state

            # Layer 1: Focused branch terrain and grid (all cells, no entities)
            self._draw_branch(
                focused_branch,
                goal_active=spec.goal_active,
                has_branched=spec.has_branched,
                animation_frame=spec.animation_frame,
                skip_terrain=False,
                skip_entities=True,  # Skip entities for now
                hidden_main=hidden_main,
                hidden_sub=hidden_sub,
                current_focus=spec.current_focus
            )

            # Layer 2: Non-focused branch terrain differences only (transparent overlay)
            # Only show terrain cells that differ from focused branch
            self._draw_branch(
                non_focused_branch,
                goal_active=spec.goal_active,
                has_branched=spec.has_branched,
                animation_frame=spec.animation_frame,
                skip_terrain=False,
                skip_entities=True,  # Skip entities for now
                terrain_diff_reference=focused_branch.state,  # Only show differences
                hidden_main=hidden_main,
                hidden_sub=hidden_sub,
                current_focus=spec.current_focus
            )

            # Layer 3: Non-focused branch entities only (transparent overlay)
            self._draw_branch(
                non_focused_branch,
                goal_active=spec.goal_active,
                has_branched=spec.has_branched,
                animation_frame=spec.animation_frame,
                skip_terrain=True,  # No terrain
                skip_entities=False,  # Draw entities
                hidden_main=hidden_main,
                hidden_sub=hidden_sub,
                current_focus=spec.current_focus
            )

            # Layer 4: Focused branch entities on top (opaque, highest layer)
            self._draw_branch(
                focused_branch,
                goal_active=spec.goal_active,
                has_branched=spec.has_branched,
                animation_frame=spec.animation_frame,
                skip_terrain=True,  # No terrain (already drawn)
                skip_entities=False,  # Draw entities on top
                hidden_main=hidden_main,
                hidden_sub=hidden_sub,
                current_focus=spec.current_focus
            )
        else:
            # Normal mode: draw in standard order
            if spec.sub_branch and -500 < spec.sub_branch.pos_x < WINDOW_WIDTH + 100:
                self._draw_branch(
                    spec.sub_branch,
                    goal_active=spec.goal_active,
                    has_branched=spec.has_branched,
                    animation_frame=spec.animation_frame
                )

            if -500 < spec.main_branch.pos_x < WINDOW_WIDTH + 100:
                self._draw_branch(
                    spec.main_branch,
                    goal_active=spec.goal_active,
                    has_branched=spec.has_branched,
                    animation_frame=spec.animation_frame
                )

        # 3. Draw debug info
        self._draw_debug_info(
            spec.step_count,
            spec.current_focus,
            spec.has_branched,
            spec.input_sequence
        )

        # 4. Overlay (collapsed or victory)
        if spec.is_collapsed:
            self._draw_overlay("FALL DOWN!", (150, 0, 0))
        elif spec.is_victory:
            self._draw_overlay("LEVEL COMPLETE!", (0, 0, 0))

    def _flip_y(self, y: int) -> int:
        """Convert top-down Y to arcade's bottom-up Y."""
        return WINDOW_HEIGHT - y

    def _grid_to_screen(self, start_x: int, start_y: int,
                        grid_x: int, grid_y: int, cell_size: int) -> Tuple[int, int]:
        """Convert grid position to screen center coordinates."""
        screen_x = start_x + grid_x * cell_size + cell_size // 2
        screen_y = self._flip_y(start_y + grid_y * cell_size + cell_size // 2)
        return screen_x, screen_y

    def _draw_branch(self, spec: 'BranchViewSpec', goal_active: bool,
                     has_branched: bool, animation_frame: int,
                     hidden_main: Optional[BranchState] = None,
                     hidden_sub: Optional[BranchState] = None,
                     current_focus: int = 0,
                     skip_terrain: bool = False,
                     skip_entities: bool = False,
                     terrain_diff_reference: Optional[BranchState] = None):
        """Draw a single branch panel.

        Args:
            terrain_diff_reference: If provided, only draw terrain cells that differ from this reference.
        """
        state = spec.state
        start_x = spec.pos_x
        start_y = spec.pos_y
        cell_size = int(CELL_SIZE * spec.scale)
        grid_width = cell_size * GRID_SIZE
        grid_height = cell_size * GRID_SIZE

        # Title
        title_y = self._flip_y(start_y - int(15 * spec.scale))
        font_size = int(14 * spec.scale)
        self._draw_cached_text(
            f'title_{spec.title}_{font_size}_{spec.alpha:.2f}', spec.title, start_x, title_y,
            (*BLACK, int(spec.alpha * 255)), font_size=font_size, anchor_x="left", anchor_y="center"
        )

        # Border
        border_width = int((5 if spec.is_focused else 3) * spec.scale)
        self._draw_rect_outline(
            start_x, start_y, grid_width, grid_height,
            (*spec.border_color, int(spec.alpha * 255)), max(1, border_width)
        )

        # Terrain (SpriteList for static, immediate mode for dynamic) - skip if requested
        if not skip_terrain:
            terrain_sprites, dynamic_cells = self._build_terrain_spritelist(
                state, start_x, start_y, cell_size,
                goal_active, has_branched, spec.highlight_branch_point,
                terrain_diff_reference
            )
            terrain_sprites.alpha = int(spec.alpha * 255)
            terrain_sprites.draw()
            self._draw_dynamic_terrain(start_x, start_y, state, cell_size,
                                       dynamic_cells, has_branched, spec.alpha,
                                       terrain_diff_reference)

        # Entities (boxes) - skip if requested
        if not skip_entities:
            for e in state.entities:
                if e.uid != 0 and e.type == EntityType.BOX:
                    self._draw_entity(start_x, start_y, e, state, cell_size, spec.alpha, spec.border_color)

            # Shadow connections (only on focused, full-scale branch)
            if spec.is_focused and spec.scale >= 1.0:
                self._draw_shadow_connections(start_x, start_y, state, animation_frame, cell_size)

            # Inherited hold hint (merge preview only)
            if spec.is_merge_preview and spec.show_inherit_hint and hidden_main and hidden_sub:
                self._draw_inherited_hold_hint(
                    start_x, start_y, state,
                    hidden_main, hidden_sub,
                    current_focus, animation_frame, cell_size
                )

            # Player
            held_items = state.get_held_items()
            held_uid = held_items[0] if held_items else None
            if held_uid:
                color_index = (held_uid - 1) % len(BOX_COLORS)
                player_color = BOX_COLORS[color_index]
            else:
                player_color = BLUE if (spec.is_focused or spec.is_merge_preview) else GRAY
            self._draw_player(start_x, start_y, state.player, player_color, held_uid, cell_size, spec.alpha)

        # Cell hint (only for focused, full-scale)
        if spec.interaction_hint and spec.scale >= 1.0:
            self._draw_cell_hint(start_x, start_y, spec.interaction_hint, cell_size, spec.alpha)

        # Grid lines (skip if terrain is skipped)
        if not skip_terrain:
            self._draw_grid_lines(start_x, start_y, state, cell_size, spec.alpha)

    def _draw_rect_outline(self, x: int, y: int, w: int, h: int,
                           color: Tuple, thickness: int):
        """Draw rectangle outline (top-down coordinates)."""
        # Convert to arcade coordinates (bottom-left origin)
        left = x
        right = x + w
        top = self._flip_y(y)
        bottom = self._flip_y(y + h)
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, color, thickness)

    def _draw_rect_filled(self, x: int, y: int, w: int, h: int, color: Tuple):
        """Draw filled rectangle (top-down coordinates)."""
        left = x
        right = x + w
        top = self._flip_y(y)
        bottom = self._flip_y(y + h)
        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)

    def _draw_terrain(self, start_x: int, start_y: int, state: BranchState,
                      cell_size: int, goal_active: bool, has_branched: bool,
                      highlight_branch_point: bool):
        """Draw terrain layer."""
        for gx in range(GRID_SIZE):
            for gy in range(GRID_SIZE):
                pos = (gx, gy)
                cell_x = start_x + gx * cell_size
                cell_y = start_y + gy * cell_size

                terrain = state.terrain.get(pos, TerrainType.FLOOR)
                center_x, center_y = self._grid_to_screen(start_x, start_y, gx, gy, cell_size)

                # Branch point highlight
                if (highlight_branch_point and pos == state.player.pos
                    and terrain in (TerrainType.BRANCH1, TerrainType.BRANCH2,
                                   TerrainType.BRANCH3, TerrainType.BRANCH4)):
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, (150, 255, 150))
                    self._draw_branch_marker(center_x, center_y, terrain, GREEN, cell_size)
                    continue

                if terrain == TerrainType.WALL:
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, BLACK)
                elif terrain == TerrainType.SWITCH:
                    activated = state.switch_activated(pos)
                    color = (200, 255, 200) if activated else (255, 200, 200)
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, color)
                elif terrain == TerrainType.NO_CARRY:
                    # Light orange background
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, (255, 240, 220))
                    # Dark orange border
                    scale = cell_size / CELL_SIZE
                    self._draw_rect_outline(cell_x, cell_y, cell_size, cell_size,
                                           (255, 140, 0), max(1, int(4 * scale)))
                    # 'c' symbol
                    arcade.draw_text('c', center_x, center_y, (255, 100, 0),
                                    font_size=int(14 * scale),
                                    anchor_x="center", anchor_y="center")
                elif terrain in (TerrainType.BRANCH1, TerrainType.BRANCH2,
                                TerrainType.BRANCH3, TerrainType.BRANCH4):
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, WHITE)
                    color = GRAY if has_branched else GREEN
                    self._draw_branch_marker(center_x, center_y, terrain, color, cell_size)
                elif terrain == TerrainType.GOAL:
                    if goal_active:
                        flash = int((time.time() * 1000 / 300) % 2)
                        color = (255, 255, 100) if flash else YELLOW
                        self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, color)
                        self._draw_rect_outline(cell_x, cell_y, cell_size, cell_size,
                                               GREEN, max(1, int(6 * cell_size / CELL_SIZE)))
                    else:
                        self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, YELLOW)
                    arcade.draw_text('Goal', center_x, center_y, BLACK,
                                    font_size=int(14 * cell_size / CELL_SIZE),
                                    anchor_x="center", anchor_y="center")
                elif terrain == TerrainType.HOLE:
                    filled = state.is_hole_filled(pos)
                    color = (160, 120, 60) if filled else (60, 40, 20)
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, color)
                else:
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, WHITE)

    def _draw_branch_marker(self, cx: int, cy: int, terrain: TerrainType,
                            color: Tuple, cell_size: int):
        """Draw concentric circles for branch point."""
        uses = {
            TerrainType.BRANCH1: 1, TerrainType.BRANCH2: 2,
            TerrainType.BRANCH3: 3, TerrainType.BRANCH4: 4
        }[terrain]

        base_radius = cell_size // 6
        ring_spacing = int(6 * cell_size / CELL_SIZE)
        line_width = max(1, int(3 * cell_size / CELL_SIZE))

        for i in range(uses - 1, 0, -1):
            radius = base_radius + i * ring_spacing
            arcade.draw_circle_outline(cx, cy, radius, color, line_width)
        arcade.draw_circle_filled(cx, cy, base_radius, color)

    def _draw_entity(self, start_x: int, start_y: int, entity,
                     state: BranchState, cell_size: int, alpha: float = 1.0,
                     branch_color: Tuple[int, int, int] = None):
        """Draw a single entity (box)."""
        scale = cell_size / CELL_SIZE
        padding = int((15 if entity.z == -1 else 9) * scale)

        gx, gy = entity.pos
        cell_x = start_x + gx * cell_size + padding
        cell_y = start_y + gy * cell_size + padding
        box_size = cell_size - padding * 2

        # Color by uid
        color_index = (entity.uid - 1) % len(BOX_COLORS)
        base_color = BOX_COLORS[color_index]

        is_shadow = state.is_shadow(entity.uid)
        is_transparent_branch = alpha < 0.9  # In merge preview overlay

        # Apply desaturation
        if is_shadow:
            display_color = desaturate_color(base_color, 0.5)
        elif is_transparent_branch:
            # Light desaturation for transparent branch in merge preview
            display_color = desaturate_color(base_color, 0.3)
        else:
            display_color = base_color

        display_color = (*display_color, int(alpha * 255))

        # Fill
        self._draw_rect_filled(cell_x, cell_y, box_size, box_size, display_color)

        # Border color and style
        if is_transparent_branch:
            # Transparent overlay: no border
            border_color = None
            border_thickness = 0
        else:
            # Normal black border
            border_color = (*BLACK, int(alpha * 255))
            border_thickness = max(1, int(2 * scale))

        # Border (dashed for shadow, solid otherwise, none for transparent overlay)
        if border_thickness > 0 and border_color is not None:
            if is_shadow:
                self._draw_dashed_rect(cell_x, cell_y, box_size, box_size,
                                      border_color, border_thickness)
            else:
                self._draw_rect_outline(cell_x, cell_y, box_size, box_size,
                                       border_color, border_thickness)

        # UID text (cached)
        center_x = cell_x + box_size // 2
        center_y = self._flip_y(cell_y + box_size // 2)
        self._draw_cached_text(f'uid_{entity.uid}_{scale:.2f}_{alpha:.2f}', str(entity.uid),
                               center_x, center_y, (*WHITE, int(alpha * 255)), font_size=int(14 * scale))

    def _draw_dashed_rect(self, x: int, y: int, w: int, h: int,
                          color: Tuple, thickness: int):
        """Draw dashed rectangle outline."""
        dash_len = 5
        gap_len = 5

        # Top edge
        for i in range(0, w, dash_len + gap_len):
            end_i = min(i + dash_len, w)
            arcade.draw_line(x + i, self._flip_y(y),
                           x + end_i, self._flip_y(y), color, thickness)
        # Bottom edge
        for i in range(0, w, dash_len + gap_len):
            end_i = min(i + dash_len, w)
            arcade.draw_line(x + i, self._flip_y(y + h),
                           x + end_i, self._flip_y(y + h), color, thickness)
        # Left edge
        for i in range(0, h, dash_len + gap_len):
            end_i = min(i + dash_len, h)
            arcade.draw_line(x, self._flip_y(y + i),
                           x, self._flip_y(y + end_i), color, thickness)
        # Right edge
        for i in range(0, h, dash_len + gap_len):
            end_i = min(i + dash_len, h)
            arcade.draw_line(x + w, self._flip_y(y + i),
                           x + w, self._flip_y(y + end_i), color, thickness)

    def _draw_player(self, start_x: int, start_y: int, player,
                     color: Tuple, held_uid: Optional[int], cell_size: int, alpha: float = 1.0):
        """Draw the player."""
        scale = cell_size / CELL_SIZE
        gx, gy = player.pos
        center_x, center_y = self._grid_to_screen(start_x, start_y, gx, gy, cell_size)

        dx, dy = player.direction
        offset = int(8 * scale)
        arrow_cx = center_x + dx * offset
        arrow_cy = center_y - dy * offset  # Flip Y for arrow

        player_color = (*color, int(alpha * 255)) if len(color) == 3 else color

        if held_uid is not None:
            # Draw box-shaped player
            pad = int(5 * scale)
            cell_x = start_x + gx * cell_size + pad
            cell_y = start_y + gy * cell_size + pad
            box_size = cell_size - pad * 2

            self._draw_rect_filled(cell_x, cell_y, box_size, box_size, player_color)
            self._draw_rect_outline(cell_x, cell_y, box_size, box_size,
                                   (*BLACK, int(alpha * 255)), max(1, int(3 * scale)))

            # UID text (cached)
            self._draw_cached_text(f'held_{held_uid}_{scale:.2f}_{alpha:.2f}', str(held_uid),
                                   center_x, center_y, (*WHITE, int(alpha * 255)), font_size=int(14 * scale))

            # Arrow
            arrow_size = int(21 * scale)
            self._draw_arrow(arrow_cx, arrow_cy, dx, -dy, arrow_size, (*BLACK, int(alpha * 255)))
        else:
            # Draw circle player
            radius = cell_size // 5
            arcade.draw_circle_filled(center_x, center_y, radius, player_color)

            arrow_size = int(21 * scale)
            self._draw_arrow(arrow_cx, arrow_cy, dx, -dy, arrow_size, (*BLACK, int(alpha * 255)))

    def _draw_arrow(self, cx: int, cy: int, dx: int, dy: int,
                    size: int, color: Tuple):
        """Draw a triangular arrow."""
        half = size // 2
        if dy == 1:  # Up (screen)
            points = [(cx, cy + size), (cx - half, cy + half), (cx + half, cy + half)]
        elif dy == -1:  # Down (screen)
            points = [(cx, cy - size), (cx - half, cy - half), (cx + half, cy - half)]
        elif dx == -1:  # Left
            points = [(cx - size, cy), (cx - half, cy - half), (cx - half, cy + half)]
        else:  # Right
            points = [(cx + size, cy), (cx + half, cy - half), (cx + half, cy + half)]
        arcade.draw_polygon_filled(points, color)

    def _draw_grid_lines(self, start_x: int, start_y: int,
                         state: BranchState, cell_size: int, alpha: float = 1.0):
        """Draw grid lines."""
        scale = cell_size / CELL_SIZE

        for gx in range(GRID_SIZE):
            for gy in range(GRID_SIZE):
                pos = (gx, gy)
                cell_x = start_x + gx * cell_size
                cell_y = start_y + gy * cell_size

                terrain = state.terrain.get(pos)

                if terrain == TerrainType.SWITCH:
                    activated = state.switch_activated(pos)
                    color = (0, 200, 0, int(alpha * 255)) if activated else (150, 0, 0, int(alpha * 255))
                    self._draw_rect_outline(cell_x, cell_y, cell_size, cell_size,
                                           color, max(1, int(5 * scale)))
                else:
                    self._draw_rect_outline(cell_x, cell_y, cell_size, cell_size, (*GRAY, int(alpha * 255)), 1)

    def _draw_shadow_connections(self, start_x: int, start_y: int,
                                  state: BranchState, animation_frame: int,
                                  cell_size: int):
        """Draw shadow connection effects."""
        if state.get_held_items():
            return

        player = state.player
        px, py = player.pos
        dx, dy = player.direction
        front_pos = (px + dx, py + dy)

        from timeline_system import Physics
        entities_at_front = [e for e in state.entities
                            if e.pos == front_pos and Physics.grounded(e)]
        if not entities_at_front:
            return

        front_uids = {e.uid for e in entities_at_front}

        for uid in front_uids:
            if not state.is_shadow(uid):
                continue

            all_instances = state.get_entities_by_uid(uid)
            positions = {e.pos for e in all_instances}

            if len(positions) <= 1:
                continue

            other_positions = positions - {front_pos}

            fx, fy = front_pos
            front_cx, front_cy = self._grid_to_screen(start_x, start_y, fx, fy, cell_size)

            line_color = (50, 220, 50)
            slow_offset = animation_frame * 0.25

            for pos in other_positions:
                ox, oy = pos
                other_cx, other_cy = self._grid_to_screen(start_x, start_y, ox, oy, cell_size)
                self._draw_dashed_line(other_cx, other_cy, front_cx, front_cy,
                                       line_color, 3, 12, slow_offset)

    def _draw_dashed_line(self, x1: int, y1: int, x2: int, y2: int,
                          color: Tuple, width: int = 3, dash_length: int = 9,
                          offset: float = 0):
        """Draw a flowing dashed line."""
        dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if dist == 0:
            return

        dx = (x2 - x1) / dist
        dy = (y2 - y1) / dist

        period = dash_length * 2
        pos = offset % period

        while pos < dist:
            seg_start = max(0.0, pos)
            seg_end = min(dist, pos + dash_length)
            if seg_end > seg_start:
                sx = int(x1 + dx * seg_start)
                sy = int(y1 + dy * seg_start)
                ex = int(x1 + dx * seg_end)
                ey = int(y1 + dy * seg_end)
                arcade.draw_line(sx, sy, ex, ey, color, width)
            pos += period

    def _draw_inherited_hold_hint(self, start_x: int, start_y: int,
                                   preview_state: BranchState,
                                   main_branch: BranchState,
                                   sub_branch: BranchState,
                                   current_focus: int,
                                   animation_frame: int,
                                   cell_size: int):
        """Show inherited hold hint for merge preview."""
        focused = sub_branch if current_focus == 1 else main_branch
        other = main_branch if current_focus == 1 else sub_branch

        other_held = set(other.get_held_items())
        focused_held = set(focused.get_held_items())
        inherited = other_held if not focused_held else set()

        if not inherited:
            return

        from timeline_system import Physics

        scale = cell_size / CELL_SIZE
        inherit_line_color = ORANGE
        converge_line_color = CYAN
        slow_offset = animation_frame * 0.25

        for uid in inherited:
            ghost_pos = other.player.pos
            gx, gy = ghost_pos

            # Ghost box
            pad = int(6 * scale)
            cell_x = start_x + gx * cell_size + pad
            cell_y = start_y + gy * cell_size + pad
            box_size = cell_size - pad * 2

            color_index = (uid - 1) % len(BOX_COLORS)
            base_color = BOX_COLORS[color_index]
            ghost_color = desaturate_color(base_color, 0.7)

            # Semi-transparent fill
            ghost_color_alpha = (*ghost_color, 128)
            self._draw_rect_filled(cell_x, cell_y, box_size, box_size, ghost_color_alpha)
            self._draw_rect_outline(cell_x, cell_y, box_size, box_size,
                                   ghost_color, max(1, int(3 * scale)))

            # UID text (cached)
            center_x = cell_x + box_size // 2
            center_y = self._flip_y(cell_y + box_size // 2)
            self._draw_cached_text(f'ghost_{uid}_{scale:.2f}', str(uid),
                                   center_x, center_y, GRAY,
                                   font_size=max(12, int(14 * scale)))

            # Converge line: focused branch instance -> other branch ghost
            focused_instances = [
                e for e in focused.entities
                if e.uid == uid and (Physics.grounded(e) or e.z == -1)
            ]
            if focused_instances:
                ghost_cx, ghost_cy = self._grid_to_screen(start_x, start_y, gx, gy, cell_size)
                for inst in focused_instances:
                    fx, fy = inst.pos
                    focused_cx, focused_cy = self._grid_to_screen(start_x, start_y, fx, fy, cell_size)
                    self._draw_dashed_line(focused_cx, focused_cy, ghost_cx, ghost_cy,
                                           converge_line_color, max(1, int(2 * scale)),
                                           int(10 * scale), slow_offset)

            # Dashed line
            ghost_cx, ghost_cy = self._grid_to_screen(start_x, start_y, gx, gy, cell_size)
            px, py = preview_state.player.pos
            player_cx, player_cy = self._grid_to_screen(start_x, start_y, px, py, cell_size)

            self._draw_dashed_line(ghost_cx, ghost_cy, player_cx, player_cy,
                                   inherit_line_color, max(1, int(3 * scale)),
                                   int(12 * scale), slow_offset)

            # Pulsing lock corners
            pulse = math.sin(animation_frame / 20) * 0.3 + 0.7
            lock_color = (
                int(inherit_line_color[0] * pulse),
                int(inherit_line_color[1] * pulse),
                int(inherit_line_color[2] * pulse)
            )
            self._draw_lock_corners(start_x, start_y, (px, py), lock_color,
                                   cell_size, size=int(24 * scale),
                                   thickness=max(1, int(8 * scale)),
                                   margin=int(5 * scale))

    def _draw_lock_corners(self, start_x: int, start_y: int, pos: Tuple[int, int],
                           color: Tuple, cell_size: int,
                           size: int = 24, thickness: int = 8, margin: int = 0):
        """Draw L-shaped corner lock brackets."""
        gx, gy = pos
        rect_x = start_x + gx * cell_size - margin
        rect_y = start_y + gy * cell_size - margin
        cell_w = cell_size + margin * 2
        cell_h = cell_size + margin * 2

        # Convert to screen coordinates
        top = self._flip_y(rect_y)
        bottom = self._flip_y(rect_y + cell_h)
        left = rect_x
        right = rect_x + cell_w

        # Top-left
        arcade.draw_line(left, top - size, left, top, color, thickness)
        arcade.draw_line(left, top, left + size, top, color, thickness)
        # Top-right
        arcade.draw_line(right - size, top, right, top, color, thickness)
        arcade.draw_line(right, top, right, top - size, color, thickness)
        # Bottom-left
        arcade.draw_line(left, bottom + size, left, bottom, color, thickness)
        arcade.draw_line(left, bottom, left + size, bottom, color, thickness)
        # Bottom-right
        arcade.draw_line(right - size, bottom, right, bottom, color, thickness)
        arcade.draw_line(right, bottom, right, bottom + size, color, thickness)

    def _draw_cell_hint(self, start_x: int, start_y: int,
                        hint: 'InteractionHint', cell_size: int, alpha: float = 1.0):
        """Draw cell interaction hint."""
        gx, gy = hint.target_pos
        cell_x = start_x + gx * cell_size
        cell_y = start_y + gy * cell_size
        center_x, center_y = self._grid_to_screen(start_x, start_y, gx, gy, cell_size)

        if hint.is_inset:
            # Inset dashed frame
            margin = 8
            self._draw_dashed_rect(
                cell_x + margin, cell_y + margin,
                cell_size - margin * 2, cell_size - margin * 2,
                (*hint.color, int(alpha * 255)), 2
            )

        # Text with outline
        white_alpha = (*WHITE, int(alpha * 255))
        black_alpha = (*BLACK, int(alpha * 255))
        self._draw_text_with_outline('[X]', center_x, center_y + 8, white_alpha, black_alpha, 12)
        self._draw_text_with_outline(hint.text, center_x, center_y - 12, white_alpha, black_alpha, 12)

    def _draw_text_with_outline(self, text: str, x: int, y: int,
                                 text_color: Tuple, outline_color: Tuple,
                                 font_size: int, outline_width: int = 2):
        """Draw text with outline for readability."""
        # Outline (8 directions)
        for dx in [-outline_width, 0, outline_width]:
            for dy in [-outline_width, 0, outline_width]:
                if dx == 0 and dy == 0:
                    continue
                arcade.draw_text(text, x + dx, y + dy, outline_color,
                               font_size=font_size,
                               anchor_x="center", anchor_y="center")
        # Main text
        arcade.draw_text(text, x, y, text_color,
                        font_size=font_size,
                        anchor_x="center", anchor_y="center")

    def _draw_tutorial(self, tutorial):
        """Draw tutorial box."""
        x, y = PADDING, 40
        width = 450
        padding_inner = 10
        line_height = 32
        title_height = 30
        height = title_height + len(tutorial.items) * line_height + padding_inner * 2

        # Background
        self._draw_rect_filled(x, y, width, height, (*HINT_BG, 240))

        # Border
        self._draw_rect_outline(x, y, width, height, (100, 100, 100), 2)

        # Title (cached)
        title_y = self._flip_y(y + padding_inner + 10)
        self._draw_cached_text('tutorial_title', tutorial.title,
                               x + padding_inner, title_y,
                               (96, 165, 250), font_size=14, anchor_x="left")

        # Items (cached)
        item_y = y + padding_inner + title_height
        for i, item in enumerate(tutorial.items):
            screen_y = self._flip_y(item_y + 12)
            # Bullet point
            self._draw_cached_text(f'bullet_{i}', "•",
                                   x + padding_inner, screen_y,
                                   (96, 165, 250), font_size=20, anchor_x="left")
            # Item text
            self._draw_cached_text(f'tutorial_item_{i}', item,
                                   x + padding_inner + 20, screen_y,
                                   (220, 220, 220), font_size=12, anchor_x="left")
            item_y += line_height

    def _draw_debug_info(self, step_count: int, focus: int,
                         has_branched: bool, input_log: List[str]):
        """Draw debug info at bottom."""
        y = self._flip_y(WINDOW_HEIGHT - 45)
        keys = ''.join(input_log[-30:])
        info = f"Step: {step_count}  |  Keys: {keys}"
        # Update cached text object
        self._debug_text.text = info
        self._debug_text.y = y
        self._debug_text.draw()

    def _draw_merge_progress(self, progress: float):
        """Draw V-key hold progress bar (top-left corner)."""
        bar_width = 120
        bar_height = 8
        x = PADDING
        y = self._flip_y(50)  # Near top

        # Background
        arcade.draw_lrbt_rectangle_filled(
            x, x + bar_width, y - bar_height // 2, y + bar_height // 2,
            (80, 80, 80)
        )

        # Fill
        fill_w = int(bar_width * progress)
        if fill_w > 0:
            color = (150, 50, 150) if progress < 1.0 else (200, 80, 200)
            arcade.draw_lrbt_rectangle_filled(
                x, x + fill_w, y - bar_height // 2, y + bar_height // 2,
                color
            )

        # Label (cached)
        label_obj = self._merge_labels['ready'] if progress >= 1.0 else self._merge_labels['merging']
        label_obj.x = x + bar_width + 8
        label_obj.y = y
        label_obj.draw()

    def _draw_merge_overlay(self, spec: 'FrameViewSpec', focused: 'BranchViewSpec'):
        """Draw merge preview overlay on focused branch."""
        cell_size = int(CELL_SIZE * focused.scale)
        grid_px = cell_size * GRID_SIZE
        margin = int(12 * focused.scale)

        # We'll draw the preview state at the focused panel's position
        # with alpha blending based on v_hold_progress
        alpha = int(255 * spec.v_hold_progress)

        # For now, just draw a semi-transparent overlay
        # Full implementation would render preview to texture
        self._draw_rect_filled(
            focused.pos_x - margin, focused.pos_y - margin,
            grid_px + margin * 2, grid_px + margin * 2,
            (150, 50, 150, int(50 * spec.v_hold_progress))
        )

    def _draw_overlay(self, text: str, color: Tuple):
        """Draw full-screen overlay (collapse/victory)."""
        # Semi-transparent background
        arcade.draw_lrbt_rectangle_filled(
            0, WINDOW_WIDTH, 0, WINDOW_HEIGHT,
            (*color, 200)
        )

        # Main text (cached)
        if "FALL" in text:
            self._overlay_texts['fall'].draw()
        else:
            self._overlay_texts['victory'].draw()

        # Hint text (cached)
        self._overlay_texts['hint'].draw()
