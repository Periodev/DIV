# renderer.py - Pygame Rendering System (Layer 3)
#
# Pure rendering layer. Receives visual specifications from presentation_model
# and draws pixels. Does NOT make game logic decisions.

import math
import time
import pygame
from timeline_system import BranchState, Physics, TerrainType, EntityType
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from presentation_model import FrameViewSpec, BranchViewSpec


def desaturate_color(color: Tuple[int, int, int], amount: float = 0.5) -> Tuple[int, int, int]:
    """
    Desaturate a color by blending towards gray.

    Args:
        color: Original RGB color (r, g, b)
        amount: Desaturation ratio 0.0-1.0 (0=no change, 1=fully gray)

    Returns:
        Desaturated RGB color
    """
    r, g, b = color
    gray = (r + g + b) / 3
    new_r = int(r + (gray - r) * amount)
    new_g = int(g + (gray - g) * amount)
    new_b = int(b + (gray - b) * amount)
    return (new_r, new_g, new_b)

# Constants
GRID_SIZE = 6
CELL_SIZE = 75  # Main grid cell size
GRID_WIDTH = GRID_SIZE * CELL_SIZE  # 450
GRID_HEIGHT = GRID_SIZE * CELL_SIZE  # 450
PADDING = 30

# New layout
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800

# Preview scaling
PREVIEW_SCALE = 0.73
PREVIEW_CELL = int(CELL_SIZE * PREVIEW_SCALE)  # 55px

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
BLUE = (0, 100, 200)
RED = (200, 50, 50)
GREEN = (50, 150, 50)
DARK_GRAY = (100, 100, 100)
YELLOW = (255, 200, 0)
PURPLE = (150, 50, 150)
CYAN = (50, 150, 200)
ORANGE = (255, 150, 50)
LIGHT_ORANGE = (255, 200, 150)

# Box colors (colorblind-friendly palette)
BOX_COLORS = [
    (230, 80, 80),    # Red
    (70, 130, 180),   # Steel Blue
    (255, 180, 0),    # Orange
]

# Hint panel colors
HINT_BG = (40, 40, 40)
HINT_GREEN = (100, 200, 100)
HINT_BLUE = (60, 100, 255)
HINT_CYAN = (0, 220, 220)
HINT_TEXT_GREEN = (150, 255, 150)
HINT_TEXT_BLUE = (180, 200, 255)
HINT_TEXT_GRAY = (200, 200, 200)


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.Font(None, 24)  # 16 * 1.5
        self.arrow_font = pygame.font.Font(None, 42)  # 28 * 1.5
        self.hint_font = pygame.font.SysFont("Microsoft YaHei", 33)  # 22 * 1.5
        self.cell_hint_font = pygame.font.SysFont("Microsoft YaHei", 18)  # Small font for cell hints


    def draw_hint_panel(self, x: int, y: int, width: int, height: int, text: str,
                        border_color: tuple, text_color: tuple):
        if not text:
            return

        panel_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        panel_surface.fill((*HINT_BG, 255)) 
        self.screen.blit(panel_surface, (x, y))

        pygame.draw.rect(self.screen, border_color, (x, y, width, height), 2)

        t = pygame.time.get_ticks() / 1000  # 轉為秒
        frequency = 2.513  # 2.5 秒一個循環

        # sin 輸出為 -1 ~ 1，透過 (0.5 + 0.5 * sin) 轉為 0 ~ 1
        # 範圍設定為 100 ~ 255：確保暗處依然可見，亮處達到全開
        alpha = int(100 + 155 * (0.5 + 0.5 * math.sin(t * frequency)))
        
        text_surface = self.hint_font.render(text, True, text_color)
        temp_surf = text_surface.copy()
        temp_surf.set_alpha(alpha)
        
        text_rect = temp_surf.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(temp_surf, text_rect)

    def draw_text_with_outline(self, text: str, pos: Tuple[int, int],
                               font: pygame.font.Font,
                               text_color: Tuple = WHITE,
                               outline_color: Tuple = BLACK,
                               outline_width: int = 2):
        """Draw text with outline for better readability."""
        x, y = pos

        # Draw 8-direction outline
        for dx in [-outline_width, 0, outline_width]:
            for dy in [-outline_width, 0, outline_width]:
                if dx == 0 and dy == 0:
                    continue
                outline_surface = font.render(text, True, outline_color)
                outline_rect = outline_surface.get_rect(center=(x + dx, y + dy))
                self.screen.blit(outline_surface, outline_rect)

        # Draw center text
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=(x, y))
        self.screen.blit(text_surface, text_rect)

    def draw_cell_hint(self, start_x: int, start_y: int,
                       pos: Tuple[int, int],
                       hint_text: str,
                       hint_color: Tuple,
                       inset: bool = False):
        """Draw dashed frame + hint text on target cell.

        Args:
            start_x, start_y: Grid origin coordinates
            pos: Target cell position (x, y)
            hint_text: Hint text (e.g. 'X Pick')
            hint_color: Frame color (green=available, red=blocked, cyan=converge)
            inset: If True, draw smaller frame inside cell (for drop hint)
        """
        x, y = pos
        cell_x = start_x + x * CELL_SIZE
        cell_y = start_y + y * CELL_SIZE

        if inset:
            # Inset frame (smaller, inside cell)
            margin = 8
            rect = pygame.Rect(
                cell_x + margin, cell_y + margin,
                CELL_SIZE - margin * 2, CELL_SIZE - margin * 2
            )
            # Draw inset dashed frame manually
            dash_len, gap_len = 6, 6
            for side in ['top', 'bottom', 'left', 'right']:
                if side == 'top':
                    for i in range(0, rect.width, dash_len + gap_len):
                        pygame.draw.line(self.screen, hint_color,
                                        (rect.left + i, rect.top),
                                        (rect.left + min(i + dash_len, rect.width), rect.top), 2)
                elif side == 'bottom':
                    for i in range(0, rect.width, dash_len + gap_len):
                        pygame.draw.line(self.screen, hint_color,
                                        (rect.left + i, rect.bottom),
                                        (rect.left + min(i + dash_len, rect.width), rect.bottom), 2)
                elif side == 'left':
                    for i in range(0, rect.height, dash_len + gap_len):
                        pygame.draw.line(self.screen, hint_color,
                                        (rect.left, rect.top + i),
                                        (rect.left, rect.top + min(i + dash_len, rect.height)), 2)
                elif side == 'right':
                    for i in range(0, rect.height, dash_len + gap_len):
                        pygame.draw.line(self.screen, hint_color,
                                        (rect.right, rect.top + i),
                                        (rect.right, rect.top + min(i + dash_len, rect.height)), 2)
            # Two-line text: [X] on top, hint_text below
            text_x = cell_x + CELL_SIZE // 2
            line1_y = cell_y + CELL_SIZE // 2 - 8
            line2_y = cell_y + CELL_SIZE // 2 + 12
            self.draw_text_with_outline('[X]', (text_x, line1_y),
                                        self.cell_hint_font, WHITE, BLACK, outline_width=1)
            self.draw_text_with_outline(hint_text, (text_x, line2_y),
                                        self.cell_hint_font, WHITE, BLACK, outline_width=1)
        else:
            # Text overlay on box (no frame, two lines)
            text_x = cell_x + CELL_SIZE // 2
            line1_y = cell_y + CELL_SIZE // 2 - 10
            line2_y = cell_y + CELL_SIZE // 2 + 12
            self.draw_text_with_outline('[X]', (text_x, line1_y),
                                        self.cell_hint_font, WHITE, BLACK, outline_width=1)
            self.draw_text_with_outline(hint_text, (text_x, line2_y),
                                        self.cell_hint_font, WHITE, BLACK, outline_width=1)

    def draw_static_hints(self):
        """Draw static hints in top-left corner."""
        text = "F5重置  方向鍵移動  Z撤銷"
        x, y = PADDING, 12
        width, height = 420, 68  # 280*1.5, 45*1.5

        # Background
        panel_surface = pygame.Surface((width, height))
        panel_surface.fill(HINT_BG)
        self.screen.blit(panel_surface, (x, y))

        # Border
        pygame.draw.rect(self.screen, HINT_TEXT_GRAY, (x, y, width, height), 2)

        # Text
        text_surface = self.hint_font.render(text, True, HINT_TEXT_GRAY)
        text_rect = text_surface.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(text_surface, text_rect)

    def draw_adaptive_hints(self, _unused, timeline_hint: str):
        """Draw timeline hint panel (interaction hint now shown in-cell)."""
        y = 12
        height = 68
        timeline_width = 170

        # Center timeline panel
        timeline_x = (WINDOW_WIDTH - timeline_width) // 2

        # Draw timeline hint (green)
        self.draw_hint_panel(timeline_x, y, timeline_width, height,
                            timeline_hint, HINT_GREEN, HINT_TEXT_GREEN)

    def draw_terrain(self, start_x: int, start_y: int, state: BranchState,
                     goal_active: bool = False, has_branched: bool = False,
                     highlight_branch_point: bool = False):
        """Draw terrain layer"""
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                pos = (x, y)
                rect = pygame.Rect(
                    start_x + x * CELL_SIZE,
                    start_y + y * CELL_SIZE,
                    CELL_SIZE, CELL_SIZE
                )

                terrain = state.terrain.get(pos, TerrainType.FLOOR)

                # Branch point highlight (player standing on it)
                if (highlight_branch_point
                    and pos == state.player.pos
                    and terrain in (TerrainType.BRANCH1, TerrainType.BRANCH2,
                                   TerrainType.BRANCH3, TerrainType.BRANCH4)):
                    pygame.draw.rect(self.screen, (150, 255, 150), rect)  # Light green
                    # Draw branch point marker
                    center = rect.center
                    color = GREEN
                    uses = {TerrainType.BRANCH1: 1, TerrainType.BRANCH2: 2,
                            TerrainType.BRANCH3: 3, TerrainType.BRANCH4: 4}[terrain]
                    base_radius = CELL_SIZE // 6
                    ring_spacing = 6
                    for i in range(uses - 1, 0, -1):
                        radius = base_radius + i * ring_spacing
                        pygame.draw.circle(self.screen, color, center, radius, 3)
                    pygame.draw.circle(self.screen, color, center, base_radius)
                    continue

                if terrain == TerrainType.WALL:
                    pygame.draw.rect(self.screen, BLACK, rect)
                elif terrain == TerrainType.SWITCH:
                    activated = any(e.pos == pos for e in state.entities)
                    color = (200, 255, 200) if activated else (255, 200, 200)
                    pygame.draw.rect(self.screen, color, rect)
                elif terrain == TerrainType.WEIGHT1:
                    pygame.draw.rect(self.screen, LIGHT_ORANGE, rect)
                    text = self.font.render('1', True, ORANGE)
                    self.screen.blit(text, text.get_rect(center=rect.center))
                elif terrain == TerrainType.WEIGHT2:
                    pygame.draw.rect(self.screen, LIGHT_ORANGE, rect)
                    text = self.font.render('2', True, ORANGE)
                    self.screen.blit(text, text.get_rect(center=rect.center))
                elif terrain in (TerrainType.BRANCH1, TerrainType.BRANCH2,
                                 TerrainType.BRANCH3, TerrainType.BRANCH4):
                    # Concentric circles: BRANCH4=3circles+dot, BRANCH3=2+dot, etc.
                    center = rect.center
                    color = GRAY if has_branched else GREEN
                    uses = {TerrainType.BRANCH1: 1, TerrainType.BRANCH2: 2,
                            TerrainType.BRANCH3: 3, TerrainType.BRANCH4: 4}[terrain]
                    # Draw circles from outer to inner
                    base_radius = CELL_SIZE // 6
                    ring_spacing = 6  # 4 * 1.5
                    for i in range(uses - 1, 0, -1):
                        radius = base_radius + i * ring_spacing
                        pygame.draw.circle(self.screen, color, center, radius, 3)  # 2 * 1.5
                    # Center dot
                    pygame.draw.circle(self.screen, color, center, base_radius)
                elif terrain == TerrainType.GOAL:
                    if goal_active:
                        flash = int((pygame.time.get_ticks() / 300) % 2)
                        color = (255, 255, 100) if flash else YELLOW
                        pygame.draw.rect(self.screen, color, rect)
                        pygame.draw.rect(self.screen, GREEN, rect, 6)  # 4 * 1.5
                    else:
                        pygame.draw.rect(self.screen, YELLOW, rect)
                    text = self.font.render('Goal', True, BLACK)
                    self.screen.blit(text, text.get_rect(center=rect.center))
                elif terrain == TerrainType.HOLE:
                    filled = state.is_hole_filled(pos)
                    if filled:
                        # Filled hole: darker ground + sunken box indicator
                        pygame.draw.rect(self.screen, (160, 120, 60), rect)
                    else:
                        pygame.draw.rect(self.screen, (60, 40, 20), rect)
                        #text = self.font.render('H', True, (150, 100, 50))
                        #self.screen.blit(text, text.get_rect(center=rect.center))
                else:
                    pygame.draw.rect(self.screen, WHITE, rect)

    def draw_entity(self, start_x: int, start_y: int, entity,
                    state: BranchState):
        """Draw a single entity (auto-assign color by uid)"""

        # Assign color by uid (uid=1,2,3 -> red/blue/orange cycle)
        if entity.type == EntityType.BOX:
            color_index = (entity.uid - 1) % len(BOX_COLORS)
            base_color = BOX_COLORS[color_index]
        else:
            base_color = DARK_GRAY  # fallback

        if entity.z == -1:
            padding = 15
        else:
            padding = 9

        x, y = entity.pos
        rect = pygame.Rect(
            start_x + x * CELL_SIZE + padding,
            start_y + y * CELL_SIZE + padding,
            CELL_SIZE - padding * 2, CELL_SIZE - padding * 2
        )

        # Desaturate color for shadow entities
        is_shadow = state.is_shadow(entity.uid)
        display_color = desaturate_color(base_color, 0.5) if is_shadow else base_color

        pygame.draw.rect(self.screen, display_color, rect)

        # Shadow: dashed border, Solid: normal border
        if is_shadow:
            dash_len, gap_len = 5, 5
            # Top
            for i in range(0, rect.width, dash_len + gap_len):
                pygame.draw.line(self.screen, BLACK,
                                (rect.left + i, rect.top),
                                (rect.left + min(i + dash_len, rect.width), rect.top), 2)
            # Bottom
            for i in range(0, rect.width, dash_len + gap_len):
                pygame.draw.line(self.screen, BLACK,
                                (rect.left + i, rect.bottom - 1),
                                (rect.left + min(i + dash_len, rect.width), rect.bottom - 1), 2)
            # Left
            for i in range(0, rect.height, dash_len + gap_len):
                pygame.draw.line(self.screen, BLACK,
                                (rect.left, rect.top + i),
                                (rect.left, rect.top + min(i + dash_len, rect.height)), 2)
            # Right
            for i in range(0, rect.height, dash_len + gap_len):
                pygame.draw.line(self.screen, BLACK,
                                (rect.right - 1, rect.top + i),
                                (rect.right - 1, rect.top + min(i + dash_len, rect.height)), 2)
        else:
            pygame.draw.rect(self.screen, BLACK, rect, 2)

        # Debug usage
        text = self.font.render(str(entity.uid), True, WHITE)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_arrow(self, cx: int, cy: int, dx: int, dy: int, size: int, color: Tuple):
        """Draw a triangular arrow pointing in direction (dx, dy)."""
        half = size // 2
        if dy == -1:  # Up
            points = [(cx, cy - size), (cx - half, cy - half), (cx + half, cy - half)]
        elif dy == 1:  # Down
            points = [(cx, cy + size), (cx - half, cy + half), (cx + half, cy + half)]
        elif dx == -1:  # Left
            points = [(cx - size, cy), (cx - half, cy - half), (cx - half, cy + half)]
        else:  # Right
            points = [(cx + size, cy), (cx + half, cy - half), (cx + half, cy + half)]
        pygame.draw.polygon(self.screen, color, points)

    def draw_player(self, start_x: int, start_y: int, player, color: Tuple,
                    held_uid: int = None):
        """Draw the player. If held_uid is set, show direction around the uid."""
        px, py = player.pos
        center_x = start_x + px * CELL_SIZE + CELL_SIZE // 2
        center_y = start_y + py * CELL_SIZE + CELL_SIZE // 2

        dx, dy = player.direction

        offset = 8  # 5 * 1.5 ≈ 8
        arrow_cx = center_x + dx * offset
        arrow_cy = center_y + dy * offset

        if held_uid is not None:
            rect = pygame.Rect(
                start_x + px * CELL_SIZE + 5,  # 3 * 1.5 ≈ 5
                start_y + py * CELL_SIZE + 5,
                CELL_SIZE - 10, CELL_SIZE - 10  # 6 * 1.5 ≈ 10
            )
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, BLACK, rect, 3)  # 2 * 1.5 ≈ 3

            # Draw uid at center, arrow at edge
            uid_text = self.font.render(str(held_uid), True, WHITE)
            uid_text_rect = uid_text.get_rect(center=(center_x, center_y))
            self.screen.blit(uid_text, uid_text_rect)

            arrow_size = 21  # 14 * 1.5
            self.draw_arrow(arrow_cx, arrow_cy, dx, dy, arrow_size, BLACK)
        else:
            pygame.draw.circle(self.screen, color, (center_x, center_y), CELL_SIZE // 5)
            self.draw_arrow(arrow_cx, arrow_cy, dx, dy, 21, BLACK)  # 14 * 1.5

    def draw_grid_lines(self, start_x: int, start_y: int, state: BranchState):
        """Draw grid lines"""
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                rect = pygame.Rect(
                    start_x + x * CELL_SIZE,
                    start_y + y * CELL_SIZE,
                    CELL_SIZE, CELL_SIZE
                )
                pos = (x, y)
                terrain = state.terrain.get(pos)

                if terrain == TerrainType.SWITCH:
                    activated = any(e.pos == pos for e in state.entities)
                    color = (0, 200, 0) if activated else (150, 0, 0)
                    pygame.draw.rect(self.screen, color, rect, 5)
                else:
                    pygame.draw.rect(self.screen, GRAY, rect, 1)  # Gray grid lines

    # ========== Scaled Drawing Methods (for Preview) ==========

    def draw_terrain_scaled(self, start_x: int, start_y: int, state: BranchState,
                            cell_size: int, goal_active: bool = False,
                            has_branched: bool = False, highlight_branch_point: bool = False):
        """Draw terrain layer with variable cell size."""
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                pos = (x, y)
                rect = pygame.Rect(
                    start_x + x * cell_size,
                    start_y + y * cell_size,
                    cell_size, cell_size
                )
                terrain = state.terrain.get(pos, TerrainType.FLOOR)

                # Branch point highlight
                if (highlight_branch_point and pos == state.player.pos
                    and terrain in (TerrainType.BRANCH1, TerrainType.BRANCH2,
                                   TerrainType.BRANCH3, TerrainType.BRANCH4)):
                    pygame.draw.rect(self.screen, (150, 255, 150), rect)
                    center = rect.center
                    uses = {TerrainType.BRANCH1: 1, TerrainType.BRANCH2: 2,
                            TerrainType.BRANCH3: 3, TerrainType.BRANCH4: 4}[terrain]
                    base_radius = cell_size // 6
                    ring_spacing = int(6 * cell_size / CELL_SIZE)
                    for i in range(uses - 1, 0, -1):
                        radius = base_radius + i * ring_spacing
                        pygame.draw.circle(self.screen, GREEN, center, radius, max(1, int(3 * cell_size / CELL_SIZE)))
                    pygame.draw.circle(self.screen, GREEN, center, base_radius)
                    continue

                if terrain == TerrainType.WALL:
                    pygame.draw.rect(self.screen, BLACK, rect)
                elif terrain == TerrainType.SWITCH:
                    activated = any(e.pos == pos for e in state.entities)
                    color = (200, 255, 200) if activated else (255, 200, 200)
                    pygame.draw.rect(self.screen, color, rect)
                elif terrain == TerrainType.WEIGHT1:
                    pygame.draw.rect(self.screen, LIGHT_ORANGE, rect)
                    text = self.font.render('1', True, ORANGE)
                    self.screen.blit(text, text.get_rect(center=rect.center))
                elif terrain == TerrainType.WEIGHT2:
                    pygame.draw.rect(self.screen, LIGHT_ORANGE, rect)
                    text = self.font.render('2', True, ORANGE)
                    self.screen.blit(text, text.get_rect(center=rect.center))
                elif terrain in (TerrainType.BRANCH1, TerrainType.BRANCH2,
                                 TerrainType.BRANCH3, TerrainType.BRANCH4):
                    center = rect.center
                    color = GRAY if has_branched else GREEN
                    uses = {TerrainType.BRANCH1: 1, TerrainType.BRANCH2: 2,
                            TerrainType.BRANCH3: 3, TerrainType.BRANCH4: 4}[terrain]
                    base_radius = cell_size // 6
                    ring_spacing = int(6 * cell_size / CELL_SIZE)
                    for i in range(uses - 1, 0, -1):
                        radius = base_radius + i * ring_spacing
                        pygame.draw.circle(self.screen, color, center, radius, max(1, int(3 * cell_size / CELL_SIZE)))
                    pygame.draw.circle(self.screen, color, center, base_radius)
                elif terrain == TerrainType.GOAL:
                    if goal_active:
                        flash = int((pygame.time.get_ticks() / 300) % 2)
                        color = (255, 255, 100) if flash else YELLOW
                        pygame.draw.rect(self.screen, color, rect)
                        pygame.draw.rect(self.screen, GREEN, rect, max(1, int(6 * cell_size / CELL_SIZE)))
                    else:
                        pygame.draw.rect(self.screen, YELLOW, rect)
                    text = self.font.render('Goal', True, BLACK)
                    self.screen.blit(text, text.get_rect(center=rect.center))
                elif terrain == TerrainType.HOLE:
                    filled = state.is_hole_filled(pos)
                    if filled:
                        pygame.draw.rect(self.screen, (160, 120, 60), rect)
                    else:
                        pygame.draw.rect(self.screen, (60, 40, 20), rect)
                else:
                    pygame.draw.rect(self.screen, WHITE, rect)

    def draw_entity_scaled(self, start_x: int, start_y: int, entity,
                           state: BranchState, cell_size: int):
        """Draw entity with variable cell size."""
        if entity.type == EntityType.BOX:
            color_index = (entity.uid - 1) % len(BOX_COLORS)
            base_color = BOX_COLORS[color_index]
        else:
            base_color = DARK_GRAY

        scale = cell_size / CELL_SIZE
        padding = int((15 if entity.z == -1 else 9) * scale)

        x, y = entity.pos
        rect = pygame.Rect(
            start_x + x * cell_size + padding,
            start_y + y * cell_size + padding,
            cell_size - padding * 2, cell_size - padding * 2
        )

        is_shadow = state.is_shadow(entity.uid)
        display_color = desaturate_color(base_color, 0.5) if is_shadow else base_color
        pygame.draw.rect(self.screen, display_color, rect)

        if is_shadow:
            dash_len = int(5 * scale)
            gap_len = int(5 * scale)
            for i in range(0, rect.width, dash_len + gap_len):
                pygame.draw.line(self.screen, BLACK,
                                (rect.left + i, rect.top),
                                (rect.left + min(i + dash_len, rect.width), rect.top), max(1, int(2 * scale)))
                pygame.draw.line(self.screen, BLACK,
                                (rect.left + i, rect.bottom - 1),
                                (rect.left + min(i + dash_len, rect.width), rect.bottom - 1), max(1, int(2 * scale)))
            for i in range(0, rect.height, dash_len + gap_len):
                pygame.draw.line(self.screen, BLACK,
                                (rect.left, rect.top + i),
                                (rect.left, rect.top + min(i + dash_len, rect.height)), max(1, int(2 * scale)))
                pygame.draw.line(self.screen, BLACK,
                                (rect.right - 1, rect.top + i),
                                (rect.right - 1, rect.top + min(i + dash_len, rect.height)), max(1, int(2 * scale)))
        else:
            pygame.draw.rect(self.screen, BLACK, rect, max(1, int(2 * scale)))
        # Debug usage
        text = self.font.render(str(entity.uid), True, WHITE)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_player_scaled(self, start_x: int, start_y: int, player, color: Tuple,
                           held_uid: int, cell_size: int):
        """Draw player with variable cell size."""
        scale = cell_size / CELL_SIZE
        px, py = player.pos
        center_x = start_x + px * cell_size + cell_size // 2
        center_y = start_y + py * cell_size + cell_size // 2

        dx, dy = player.direction
        offset = int(8 * scale)
        arrow_cx = center_x + dx * offset
        arrow_cy = center_y + dy * offset

        if held_uid is not None:
            pad = int(5 * scale)
            rect = pygame.Rect(
                start_x + px * cell_size + pad,
                start_y + py * cell_size + pad,
                cell_size - pad * 2, cell_size - pad * 2
            )
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, BLACK, rect, max(1, int(3 * scale)))
            arrow_size = int(21 * scale)
            self.draw_arrow(arrow_cx, arrow_cy, dx, dy, arrow_size, BLACK)

            uid_text = self.font.render(str(held_uid), True, WHITE)
            uid_text_rect = uid_text.get_rect(center=(center_x, center_y))
            self.screen.blit(uid_text, uid_text_rect)

        else:
            pygame.draw.circle(self.screen, color, (center_x, center_y), cell_size // 5)
            self.draw_arrow(arrow_cx, arrow_cy, dx, dy, int(21 * scale), BLACK)

    def draw_grid_lines_scaled(self, start_x: int, start_y: int, state: BranchState, cell_size: int):
        """Draw grid lines with variable cell size."""
        scale = cell_size / CELL_SIZE
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                rect = pygame.Rect(
                    start_x + x * cell_size,
                    start_y + y * cell_size,
                    cell_size, cell_size
                )
                pos = (x, y)
                terrain = state.terrain.get(pos)

                if terrain == TerrainType.SWITCH:
                    activated = any(e.pos == pos for e in state.entities)
                    color = (0, 200, 0) if activated else (150, 0, 0)
                    pygame.draw.rect(self.screen, color, rect, max(1, int(5 * scale)))
                else:
                    pygame.draw.rect(self.screen, GRAY, rect, 1)

    def draw_inherited_hold_hint_scaled(self, start_x: int, start_y: int,
                                        preview_state: BranchState,
                                        main_branch: BranchState,
                                        sub_branch: BranchState,
                                        current_focus: int,
                                        animation_offset: int,
                                        cell_size: int):
        """Show inherited hold hint for scaled preview (full version)."""
        focused = sub_branch if current_focus == 1 else main_branch
        other = main_branch if current_focus == 1 else sub_branch

        other_held = set(other.get_held_items())
        focused_held = set(focused.get_held_items())
        inherited = other_held if not focused_held else set()

        if not inherited:
            return

        scale = cell_size / CELL_SIZE
        inherit_line_color = ORANGE
        slow_offset = animation_offset * 0.25

        for uid in inherited:
            ghost_pos = other.player.pos
            gx, gy = ghost_pos

            # Draw full ghost box (same as draw_ghost_box but scaled)
            pad = int(6 * scale)
            ghost_rect = pygame.Rect(
                start_x + gx * cell_size + pad,
                start_y + gy * cell_size + pad,
                cell_size - pad * 2, cell_size - pad * 2
            )
            color_index = (uid - 1) % len(BOX_COLORS)
            base_color = BOX_COLORS[color_index]
            ghost_color = desaturate_color(base_color, 0.7)

            # Semi-transparent fill
            ghost_surface = pygame.Surface((ghost_rect.width, ghost_rect.height))
            ghost_surface.set_alpha(128)
            ghost_surface.fill(ghost_color)
            self.screen.blit(ghost_surface, (ghost_rect.x, ghost_rect.y))

            # Border outline
            pygame.draw.rect(self.screen, ghost_color, ghost_rect, max(1, int(3 * scale)))

            # UID text (scaled font)
            scaled_font = pygame.font.Font(None, max(12, int(24 * scale)))
            text = scaled_font.render(str(uid), True, GRAY)
            self.screen.blit(text, text.get_rect(center=ghost_rect.center))

            # Dashed line from ghost to player
            ghost_center = (
                start_x + ghost_pos[0] * cell_size + cell_size // 2,
                start_y + ghost_pos[1] * cell_size + cell_size // 2
            )
            player_pos = preview_state.player.pos
            player_center = (
                start_x + player_pos[0] * cell_size + cell_size // 2,
                start_y + player_pos[1] * cell_size + cell_size // 2
            )
            self.draw_dashed_line(ghost_center, player_center,
                                  inherit_line_color, max(1, int(3 * scale)),
                                  int(12 * scale), slow_offset)

            # Pulsing lock corners on player position
            pulse = math.sin(animation_offset / 20) * 0.3 + 0.7
            lock_color = (int(inherit_line_color[0] * pulse),
                          int(inherit_line_color[1] * pulse),
                          int(inherit_line_color[2] * pulse))
            self.draw_lock_corners_scaled(start_x, start_y, player_pos, lock_color,
                                          cell_size, size=int(24 * scale),
                                          thickness=max(1, int(8 * scale)),
                                          margin=int(5 * scale))

    def draw_lock_corners_scaled(self, start_x: int, start_y: int, pos: Tuple[int, int],
                                  color: Tuple, cell_size: int,
                                  size: int = 24, thickness: int = 8, margin: int = 0):
        """Draw L-shaped corner lock brackets (scaled version)."""
        x, y = pos
        rect_x = start_x + x * cell_size - margin
        rect_y = start_y + y * cell_size - margin
        cell_w = cell_size + margin * 2
        cell_h = cell_size + margin * 2

        # Top-left
        pygame.draw.line(self.screen, color,
                         (rect_x, rect_y + size), (rect_x, rect_y), thickness)
        pygame.draw.line(self.screen, color,
                         (rect_x, rect_y), (rect_x + size, rect_y), thickness)
        # Top-right
        pygame.draw.line(self.screen, color,
                         (rect_x + cell_w - size, rect_y),
                         (rect_x + cell_w, rect_y), thickness)
        pygame.draw.line(self.screen, color,
                         (rect_x + cell_w, rect_y),
                         (rect_x + cell_w, rect_y + size), thickness)
        # Bottom-left
        pygame.draw.line(self.screen, color,
                         (rect_x, rect_y + cell_h - size),
                         (rect_x, rect_y + cell_h), thickness)
        pygame.draw.line(self.screen, color,
                         (rect_x, rect_y + cell_h),
                         (rect_x + size, rect_y + cell_h), thickness)
        # Bottom-right
        pygame.draw.line(self.screen, color,
                         (rect_x + cell_w - size, rect_y + cell_h),
                         (rect_x + cell_w, rect_y + cell_h), thickness)
        pygame.draw.line(self.screen, color,
                         (rect_x + cell_w, rect_y + cell_h),
                         (rect_x + cell_w, rect_y + cell_h - size), thickness)

    def draw_dashed_line(self, start: Tuple[int, int], end: Tuple[int, int],
                         color: Tuple, width: int = 3, dash_length: int = 9,
                         offset: float = 0):
        """Draw a flowing dashed line by shifting a repeating dash pattern."""
        x1, y1 = start
        x2, y2 = end
        dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        if dist == 0:
            return

        dx = (x2 - x1) / dist
        dy = (y2 - y1) / dist

        period = dash_length * 2
        # Start before the line so partial dashes entering from the start are visible
        pos = (offset % period)

        while pos < dist:
            seg_start = max(0.0, pos)
            seg_end = min(dist, pos + dash_length)
            if seg_end > seg_start:
                sx = int(x1 + dx * seg_start)
                sy = int(y1 + dy * seg_start)
                ex = int(x1 + dx * seg_end)
                ey = int(y1 + dy * seg_end)
                pygame.draw.line(self.screen, color, (sx, sy), (ex, ey), width)
            pos += period

    def draw_lock_corners(self, start_x: int, start_y: int, pos: Tuple[int, int],
                          color: Tuple, size: int = 24, thickness: int = 8,
                          margin: int = 0):
        """Draw L-shaped corner lock brackets.

        Args:
            size: L-segment length
            thickness: Line thickness
            margin: Outward extension in pixels (positive = extends beyond cell)
        """
        x, y = pos
        rect_x = start_x + x * CELL_SIZE - margin
        rect_y = start_y + y * CELL_SIZE - margin
        cell_w = CELL_SIZE + margin * 2
        cell_h = CELL_SIZE + margin * 2

        # Top-left
        pygame.draw.line(self.screen, color,
                         (rect_x, rect_y + size), (rect_x, rect_y), thickness)
        pygame.draw.line(self.screen, color,
                         (rect_x, rect_y), (rect_x + size, rect_y), thickness)
        # Top-right
        pygame.draw.line(self.screen, color,
                         (rect_x + cell_w - size, rect_y),
                         (rect_x + cell_w, rect_y), thickness)
        pygame.draw.line(self.screen, color,
                         (rect_x + cell_w, rect_y),
                         (rect_x + cell_w, rect_y + size), thickness)
        # Bottom-left
        pygame.draw.line(self.screen, color,
                         (rect_x, rect_y + cell_h - size),
                         (rect_x, rect_y + cell_h), thickness)
        pygame.draw.line(self.screen, color,
                         (rect_x, rect_y + cell_h),
                         (rect_x + size, rect_y + cell_h), thickness)
        # Bottom-right
        pygame.draw.line(self.screen, color,
                         (rect_x + cell_w - size, rect_y + cell_h),
                         (rect_x + cell_w, rect_y + cell_h), thickness)
        pygame.draw.line(self.screen, color,
                         (rect_x + cell_w, rect_y + cell_h),
                         (rect_x + cell_w, rect_y + cell_h - size), thickness)

    def draw_dashed_frame(self, start_x: int, start_y: int, pos: Tuple[int, int],
                          color: Tuple, thickness: int = 2):
        """Draw a static dashed border"""
        x, y = pos
        rect_x = start_x + x * CELL_SIZE
        rect_y = start_y + y * CELL_SIZE

        dash_length = 8  # 5 * 1.5 ≈ 8
        gap_length = 8

        for side in ['top', 'bottom', 'left', 'right']:
            if side == 'top':
                for i in range(0, CELL_SIZE, dash_length + gap_length):
                    pygame.draw.line(self.screen, color,
                                     (rect_x + i, rect_y),
                                     (rect_x + min(i + dash_length, CELL_SIZE), rect_y),
                                     thickness)
            elif side == 'bottom':
                for i in range(0, CELL_SIZE, dash_length + gap_length):
                    pygame.draw.line(self.screen, color,
                                     (rect_x + i, rect_y + CELL_SIZE),
                                     (rect_x + min(i + dash_length, CELL_SIZE), rect_y + CELL_SIZE),
                                     thickness)
            elif side == 'left':
                for i in range(0, CELL_SIZE, dash_length + gap_length):
                    pygame.draw.line(self.screen, color,
                                     (rect_x, rect_y + i),
                                     (rect_x, rect_y + min(i + dash_length, CELL_SIZE)),
                                     thickness)
            elif side == 'right':
                for i in range(0, CELL_SIZE, dash_length + gap_length):
                    pygame.draw.line(self.screen, color,
                                     (rect_x + CELL_SIZE, rect_y + i),
                                     (rect_x + CELL_SIZE, rect_y + min(i + dash_length, CELL_SIZE)),
                                     thickness)

    def draw_shadow_connections(self, start_x: int, start_y: int, state: BranchState,
                                animation_offset: int):
        """
        Draw shadow connection effects.

        When the player faces a shadow block:
        - Flowing dashed lines from other shadow positions to the front block
        - L-shaped pulsing lock brackets on the front block
        - Static dashed frames on other shadow positions
        """
        # Skip if player is holding something (can't interact with shadow)
        if state.get_held_items():
            return

        player = state.player
        px, py = player.pos
        dx, dy = player.direction
        front_pos = (px + dx, py + dy)

        # Check if there are entities at the front position
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

            front_center = (
                start_x + front_pos[0] * CELL_SIZE + CELL_SIZE // 2,
                start_y + front_pos[1] * CELL_SIZE + CELL_SIZE // 2
            )

            line_color = (50, 220, 50)

            # Draw flowing dashed lines from other positions to front (slow flow)
            slow_offset = animation_offset * 0.25
            for pos in other_positions:
                other_center = (
                    start_x + pos[0] * CELL_SIZE + CELL_SIZE // 2,
                    start_y + pos[1] * CELL_SIZE + CELL_SIZE // 2
                )
                self.draw_dashed_line(other_center, front_center,
                                      line_color, 3, 12, slow_offset)  # 2*1.5, 8*1.5


    def draw_ghost_box(self, start_x: int, start_y: int, pos: Tuple[int, int],
                       uid: int):
        """Draw a semi-transparent ghost box (auto-assign color by uid)."""
        # Get color by uid
        color_index = (uid - 1) % len(BOX_COLORS)
        base_color = BOX_COLORS[color_index]

        x, y = pos
        rect = pygame.Rect(
            start_x + x * CELL_SIZE + 6,
            start_y + y * CELL_SIZE + 6,
            CELL_SIZE - 12, CELL_SIZE - 12
        )

        ghost_surface = pygame.Surface((rect.width, rect.height))
        ghost_surface.set_alpha(128)
        ghost_color = desaturate_color(base_color, 0.7)
        ghost_surface.fill(ghost_color)
        self.screen.blit(ghost_surface, (rect.x, rect.y))

        pygame.draw.rect(self.screen, ghost_color, rect, 3)

        text = self.font.render(str(uid), True, GRAY)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_inherited_hold_hint(self, start_x: int, start_y: int,
                                  preview_state: BranchState,
                                  main_branch: BranchState,
                                  sub_branch: BranchState,
                                  current_focus: int,
                                  animation_offset: int):
        """Show inherited hold hint for the non-focused branch's held items."""
        focused = sub_branch if current_focus == 1 else main_branch
        other = main_branch if current_focus == 1 else sub_branch

        other_held = set(other.get_held_items())
        focused_held = set(focused.get_held_items())
        # Only inherit if focused is not holding anything; otherwise other's items drop
        inherited = other_held if not focused_held else set()

        if not inherited:
            return

        inherit_line_color = ORANGE
        slow_offset = animation_offset * 0.25

        for uid in inherited:
            ghost_pos = other.player.pos
            self.draw_ghost_box(start_x, start_y, ghost_pos, uid)

            ghost_center = (
                start_x + ghost_pos[0] * CELL_SIZE + CELL_SIZE // 2,
                start_y + ghost_pos[1] * CELL_SIZE + CELL_SIZE // 2
            )
            player_pos = preview_state.player.pos
            player_center = (
                start_x + player_pos[0] * CELL_SIZE + CELL_SIZE // 2,
                start_y + player_pos[1] * CELL_SIZE + CELL_SIZE // 2
            )

            self.draw_dashed_line(ghost_center, player_center,
                                  inherit_line_color, 3, 12, slow_offset)  # 2*1.5, 8*1.5

            pulse = math.sin(animation_offset / 20) * 0.3 + 0.7
            lock_color = (int(inherit_line_color[0] * pulse),
                          int(inherit_line_color[1] * pulse),
                          int(inherit_line_color[2] * pulse))
            self.draw_lock_corners(start_x, start_y, player_pos, lock_color,
                                   size=24, thickness=8, margin=5)  # 16*1.5, 5*1.5≈8, 3*1.5≈5

    def draw_overlay(self, text: str, color: Tuple):
        """Draw overlay"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(color)
        self.screen.blit(overlay, (0, 0))

        big_font = pygame.font.Font(None, 108)  # 72 * 1.5
        big_text = big_font.render(text, True, YELLOW)
        self.screen.blit(big_text,
                         big_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 60)))  # 40 * 1.5

        hint = self.font.render("F5 restart Z undo", True, WHITE)
        self.screen.blit(hint,
                         hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30)))  # 20 * 1.5

    def draw_debug_info(self, history_len: int, focus: int, has_branched: bool, input_log: list):
        """Draw debug information at bottom of screen."""
        y = WINDOW_HEIGHT - 45  # 30 * 1.5
        keys = ''.join(input_log[-30:])  # Show last 30 keys
        info = f"Step: {history_len}  |  Keys: {keys}"
        text = self.font.render(info, True, DARK_GRAY)
        self.screen.blit(text, (PADDING, y))

    # ========== New Presentation Model Interface ==========

    def draw_frame(self, spec: 'FrameViewSpec'):
        """
        Main entry point for rendering a complete frame.

        Uses positions and scale from specs for flexible layout.
        """
        # 1. Clear screen
        self.screen.fill((255, 255, 255))

        # 2. Draw tutorial box (top-left)
        if spec.tutorial and spec.tutorial.visible:
            self.draw_tutorial(spec.tutorial)

        # 3. Draw merge preview (bottom-left, scaled)
        self.draw_branch(
            spec.merge_preview,
            goal_active=spec.goal_active,
            has_branched=spec.has_branched,
            animation_frame=spec.animation_frame,
            hidden_main=spec.hidden_main,
            hidden_sub=spec.hidden_sub,
            current_focus=spec.current_focus
        )

        # 4. Draw main branch (uses position from spec)
        self.draw_branch(
            spec.main_branch,
            goal_active=spec.goal_active,
            has_branched=spec.has_branched,
            animation_frame=spec.animation_frame
        )

        # 5. Draw sub branch (if exists)
        if spec.sub_branch:
            self.draw_branch(
                spec.sub_branch,
                goal_active=spec.goal_active,
                has_branched=spec.has_branched,
                animation_frame=spec.animation_frame
            )

        # 6. Draw debug info
        self.draw_debug_info(
            spec.step_count,
            spec.current_focus,
            spec.has_branched,
            spec.input_sequence
        )

        # 7. Draw overlay (if collapsed or victory)
        if spec.is_collapsed:
            self.draw_overlay("FALL DOWN!", (150, 0, 0))
        elif spec.is_victory:
            self.draw_overlay("LEVEL COMPLETE!", (0, 0, 0))

    def draw_tutorial(self, tutorial: 'TutorialSpec'):
        """Draw tutorial box with bullet points (top-left)."""
        x, y = PADDING, 40
        width = 450
        padding_inner = 10

        # Calculate height based on items
        line_height = 32
        title_height = 30
        height = title_height + len(tutorial.items) * line_height + padding_inner * 2

        # Background
        panel_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        panel_surface.fill((40, 40, 40, 240))
        self.screen.blit(panel_surface, (x, y))

        # Border
        pygame.draw.rect(self.screen, (100, 100, 100), (x, y, width, height), 2)

        # Title (smaller font)
        title_color = (96, 165, 250)  # Light blue
        title_surface = self.font.render(tutorial.title, True, title_color)
        self.screen.blit(title_surface, (x + padding_inner, y + padding_inner))

        # Items with bullets
        item_y = y + padding_inner + title_height
        bullet_color = (96, 165, 250)
        text_color = (220, 220, 220)

        for item in tutorial.items:
            # Bullet
            bullet_surface = self.hint_font.render("•", True, bullet_color)
            self.screen.blit(bullet_surface, (x + padding_inner, item_y))
            # Text
            text_surface = self.cell_hint_font.render(item, True, text_color)
            self.screen.blit(text_surface, (x + padding_inner + 20, item_y + 5))
            item_y += line_height

    def draw_branch(
        self,
        spec: 'BranchViewSpec',
        goal_active: bool,
        has_branched: bool,
        animation_frame: int,
        hidden_main: Optional[BranchState] = None,
        hidden_sub: Optional[BranchState] = None,
        current_focus: int = 0
    ):
        """
        Draw a branch panel from a BranchViewSpec.

        Uses position and scale from spec for flexible layout.
        """
        state = spec.state
        start_x = spec.pos_x
        start_y = spec.pos_y
        cell_size = int(CELL_SIZE * spec.scale)
        grid_width = cell_size * GRID_SIZE
        grid_height = cell_size * GRID_SIZE

        # Title (smaller font for scaled panels)
        title_font = self.font if spec.scale >= 1.0 else pygame.font.Font(None, int(24 * spec.scale))
        self.screen.blit(title_font.render(spec.title, True, BLACK),
                         (start_x, start_y - int(25 * spec.scale)))

        # Focus highlight border
        if spec.is_focused:
            margin = int(12 * spec.scale)
            highlight_rect = pygame.Rect(
                start_x - margin, start_y - margin,
                grid_width + margin * 2, grid_height + margin * 2
            )
            pygame.draw.rect(self.screen, BLUE, highlight_rect, int(8 * spec.scale))

        # Border
        border_width = int((5 if spec.is_focused else 3) * spec.scale)
        pygame.draw.rect(self.screen, spec.border_color,
                         (start_x, start_y, grid_width, grid_height), max(1, border_width))

        # Terrain
        self.draw_terrain_scaled(start_x, start_y, state, cell_size,
                                 goal_active, has_branched,
                                 highlight_branch_point=spec.highlight_branch_point)

        # Entities (non-player boxes)
        for e in state.entities:
            if e.uid != 0 and e.type == EntityType.BOX:
                self.draw_entity_scaled(start_x, start_y, e, state, cell_size)

        # Shadow connections (only on focused branch, skip for scaled preview)
        if spec.is_focused and spec.scale >= 1.0:
            self.draw_shadow_connections(start_x, start_y, state, animation_frame)

        # Inherited hold hint (only for merge preview)
        if spec.is_merge_preview and hidden_main and hidden_sub:
            self.draw_inherited_hold_hint_scaled(start_x, start_y, state,
                                                 hidden_main, hidden_sub,
                                                 current_focus, animation_frame, cell_size)

        # Player
        held_items = state.get_held_items()
        held_uid = held_items[0] if held_items else None
        if held_uid:
            color_index = (held_uid - 1) % len(BOX_COLORS)
            player_color = BOX_COLORS[color_index]
        else:
            player_color = BLUE if (spec.is_focused or spec.is_merge_preview) else GRAY
        self.draw_player_scaled(start_x, start_y, state.player, player_color, held_uid, cell_size)

        # Cell hint (only if spec has interaction_hint, skip for scaled)
        if spec.interaction_hint and spec.scale >= 1.0:
            hint = spec.interaction_hint
            self.draw_cell_hint(start_x, start_y, hint.target_pos,
                               hint.text, hint.color, inset=hint.is_inset)

        # Grid lines
        self.draw_grid_lines_scaled(start_x, start_y, state, cell_size)
