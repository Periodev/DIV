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

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
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

    def draw_frame(self, spec: 'FrameViewSpec'):
        """Main entry point for rendering a complete frame."""
        # 1. Clear screen (white background)
        arcade.draw_lrbt_rectangle_filled(
            0, WINDOW_WIDTH, 0, WINDOW_HEIGHT, WHITE
        )

        # 2. Draw tutorial box
        if spec.tutorial and spec.tutorial.visible:
            self._draw_tutorial(spec.tutorial)

        # 3. Draw merge preview (bottom-left, scaled)
        self._draw_branch(
            spec.merge_preview,
            goal_active=spec.goal_active,
            has_branched=spec.has_branched,
            animation_frame=spec.animation_frame,
            hidden_main=spec.hidden_main,
            hidden_sub=spec.hidden_sub,
            current_focus=spec.current_focus
        )

        # 4. Draw main branch
        self._draw_branch(
            spec.main_branch,
            goal_active=spec.goal_active,
            has_branched=spec.has_branched,
            animation_frame=spec.animation_frame
        )

        # 5. Draw sub branch (if exists)
        if spec.sub_branch:
            self._draw_branch(
                spec.sub_branch,
                goal_active=spec.goal_active,
                has_branched=spec.has_branched,
                animation_frame=spec.animation_frame
            )

        # 6. Draw debug info
        self._draw_debug_info(
            spec.step_count,
            spec.current_focus,
            spec.has_branched,
            spec.input_sequence
        )

        # 7. V-key hold progress
        if spec.v_hold_progress > 0 and spec.has_branched:
            focused = spec.main_branch if spec.current_focus == 0 else spec.sub_branch
            if focused:
                self._draw_merge_overlay(spec, focused)
            self._draw_merge_progress(spec.v_hold_progress)

        # 8. Overlay (collapsed or victory)
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
                     current_focus: int = 0):
        """Draw a single branch panel."""
        state = spec.state
        start_x = spec.pos_x
        start_y = spec.pos_y
        cell_size = int(CELL_SIZE * spec.scale)
        grid_width = cell_size * GRID_SIZE
        grid_height = cell_size * GRID_SIZE

        # Title
        title_y = self._flip_y(start_y - int(15 * spec.scale))
        arcade.draw_text(
            spec.title, start_x, title_y,
            BLACK, font_size=int(14 * spec.scale),
            anchor_x="left", anchor_y="center"
        )

        # Focus highlight border
        if spec.is_focused:
            margin = int(12 * spec.scale)
            self._draw_rect_outline(
                start_x - margin, start_y - margin,
                grid_width + margin * 2, grid_height + margin * 2,
                BLUE, int(8 * spec.scale)
            )

        # Border
        border_width = int((5 if spec.is_focused else 3) * spec.scale)
        self._draw_rect_outline(
            start_x, start_y, grid_width, grid_height,
            spec.border_color, max(1, border_width)
        )

        # Terrain
        self._draw_terrain(start_x, start_y, state, cell_size,
                          goal_active, has_branched,
                          highlight_branch_point=spec.highlight_branch_point)

        # Entities (boxes)
        for e in state.entities:
            if e.uid != 0 and e.type == EntityType.BOX:
                self._draw_entity(start_x, start_y, e, state, cell_size)

        # Shadow connections (only on focused, full-scale branch)
        if spec.is_focused and spec.scale >= 1.0:
            self._draw_shadow_connections(start_x, start_y, state, animation_frame, cell_size)

        # Inherited hold hint (merge preview only)
        if spec.is_merge_preview and hidden_main and hidden_sub:
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
        self._draw_player(start_x, start_y, state.player, player_color, held_uid, cell_size)

        # Cell hint (only for focused, full-scale)
        if spec.interaction_hint and spec.scale >= 1.0:
            self._draw_cell_hint(start_x, start_y, spec.interaction_hint, cell_size)

        # Grid lines
        self._draw_grid_lines(start_x, start_y, state, cell_size)

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
                    activated = any(e.pos == pos for e in state.entities)
                    color = (200, 255, 200) if activated else (255, 200, 200)
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, color)
                elif terrain == TerrainType.WEIGHT1:
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, LIGHT_ORANGE)
                    arcade.draw_text('1', center_x, center_y, ORANGE,
                                    font_size=int(14 * cell_size / CELL_SIZE),
                                    anchor_x="center", anchor_y="center")
                elif terrain == TerrainType.WEIGHT2:
                    self._draw_rect_filled(cell_x, cell_y, cell_size, cell_size, LIGHT_ORANGE)
                    arcade.draw_text('2', center_x, center_y, ORANGE,
                                    font_size=int(14 * cell_size / CELL_SIZE),
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
                     state: BranchState, cell_size: int):
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
        display_color = desaturate_color(base_color, 0.5) if is_shadow else base_color

        # Fill
        self._draw_rect_filled(cell_x, cell_y, box_size, box_size, display_color)

        # Border (dashed for shadow, solid otherwise)
        if is_shadow:
            self._draw_dashed_rect(cell_x, cell_y, box_size, box_size,
                                  BLACK, max(1, int(2 * scale)))
        else:
            self._draw_rect_outline(cell_x, cell_y, box_size, box_size,
                                   BLACK, max(1, int(2 * scale)))

        # UID text
        center_x = cell_x + box_size // 2
        center_y = self._flip_y(cell_y + box_size // 2)
        arcade.draw_text(str(entity.uid), center_x, center_y, WHITE,
                        font_size=int(14 * scale),
                        anchor_x="center", anchor_y="center")

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
                     color: Tuple, held_uid: Optional[int], cell_size: int):
        """Draw the player."""
        scale = cell_size / CELL_SIZE
        gx, gy = player.pos
        center_x, center_y = self._grid_to_screen(start_x, start_y, gx, gy, cell_size)

        dx, dy = player.direction
        offset = int(8 * scale)
        arrow_cx = center_x + dx * offset
        arrow_cy = center_y - dy * offset  # Flip Y for arrow

        if held_uid is not None:
            # Draw box-shaped player
            pad = int(5 * scale)
            cell_x = start_x + gx * cell_size + pad
            cell_y = start_y + gy * cell_size + pad
            box_size = cell_size - pad * 2

            self._draw_rect_filled(cell_x, cell_y, box_size, box_size, color)
            self._draw_rect_outline(cell_x, cell_y, box_size, box_size,
                                   BLACK, max(1, int(3 * scale)))

            # UID text
            arcade.draw_text(str(held_uid), center_x, center_y, WHITE,
                            font_size=int(14 * scale),
                            anchor_x="center", anchor_y="center")

            # Arrow
            arrow_size = int(21 * scale)
            self._draw_arrow(arrow_cx, arrow_cy, dx, -dy, arrow_size, BLACK)
        else:
            # Draw circle player
            radius = cell_size // 5
            arcade.draw_circle_filled(center_x, center_y, radius, color)

            arrow_size = int(21 * scale)
            self._draw_arrow(arrow_cx, arrow_cy, dx, -dy, arrow_size, BLACK)

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
                         state: BranchState, cell_size: int):
        """Draw grid lines."""
        scale = cell_size / CELL_SIZE

        for gx in range(GRID_SIZE):
            for gy in range(GRID_SIZE):
                pos = (gx, gy)
                cell_x = start_x + gx * cell_size
                cell_y = start_y + gy * cell_size

                terrain = state.terrain.get(pos)

                if terrain == TerrainType.SWITCH:
                    activated = any(e.pos == pos for e in state.entities)
                    color = (0, 200, 0) if activated else (150, 0, 0)
                    self._draw_rect_outline(cell_x, cell_y, cell_size, cell_size,
                                           color, max(1, int(5 * scale)))
                else:
                    self._draw_rect_outline(cell_x, cell_y, cell_size, cell_size, GRAY, 1)

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

        scale = cell_size / CELL_SIZE
        inherit_line_color = ORANGE
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

            # UID text
            center_x = cell_x + box_size // 2
            center_y = self._flip_y(cell_y + box_size // 2)
            arcade.draw_text(str(uid), center_x, center_y, GRAY,
                            font_size=max(12, int(14 * scale)),
                            anchor_x="center", anchor_y="center")

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
                        hint: 'InteractionHint', cell_size: int):
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
                hint.color, 2
            )

        # Text with outline
        self._draw_text_with_outline('[X]', center_x, center_y + 8, WHITE, BLACK, 12)
        self._draw_text_with_outline(hint.text, center_x, center_y - 12, WHITE, BLACK, 12)

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

        # Title
        title_y = self._flip_y(y + padding_inner + 10)
        arcade.draw_text(tutorial.title, x + padding_inner, title_y,
                        (96, 165, 250), font_size=14,
                        anchor_x="left", anchor_y="center")

        # Items
        item_y = y + padding_inner + title_height
        for item in tutorial.items:
            screen_y = self._flip_y(item_y + 12)
            arcade.draw_text("•", x + padding_inner, screen_y,
                           (96, 165, 250), font_size=20,
                           anchor_x="left", anchor_y="center")
            arcade.draw_text(item, x + padding_inner + 20, screen_y,
                           (220, 220, 220), font_size=12,
                           anchor_x="left", anchor_y="center")
            item_y += line_height

    def _draw_debug_info(self, step_count: int, focus: int,
                         has_branched: bool, input_log: List[str]):
        """Draw debug info at bottom."""
        y = self._flip_y(WINDOW_HEIGHT - 45)
        keys = ''.join(input_log[-30:])
        info = f"Step: {step_count}  |  Keys: {keys}"
        arcade.draw_text(info, PADDING, y, DARK_GRAY, font_size=14,
                        anchor_x="left", anchor_y="center")

    def _draw_merge_progress(self, progress: float):
        """Draw V-key hold progress bar."""
        bar_width = 120
        bar_height = 8
        x = PADDING
        y = self._flip_y(300)

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

        # Label
        label = "合併" if progress >= 1.0 else "... Merge"
        arcade.draw_text(label, x + bar_width + 8, y,
                        (150, 50, 150), font_size=14,
                        anchor_x="left", anchor_y="center")

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

        # Main text
        arcade.draw_text(text, WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60,
                        YELLOW, font_size=72,
                        anchor_x="center", anchor_y="center")

        # Hint text
        arcade.draw_text("F5 restart Z undo", WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30,
                        WHITE, font_size=14,
                        anchor_x="center", anchor_y="center")
