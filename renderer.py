# renderer.py - Pygame Rendering System

import math
import pygame
from timeline_system import BranchState, Physics, TerrainType, EntityType
from typing import Optional, Tuple


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
CELL_SIZE = 50
GRID_WIDTH = GRID_SIZE * CELL_SIZE
GRID_HEIGHT = GRID_SIZE * CELL_SIZE
PADDING = 20
WINDOW_WIDTH = GRID_WIDTH * 3 + PADDING * 4
WINDOW_HEIGHT = GRID_HEIGHT + PADDING * 2 + 40

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


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.Font(None, 16)
        self.arrow_font = pygame.font.Font(None, 28)

    def draw_terrain(self, start_x: int, start_y: int, state: BranchState,
                     goal_active: bool = False, has_branched: bool = False):
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
                elif terrain == TerrainType.BRANCH:
                    # Small branch point indicator
                    center = rect.center
                    color = GRAY if (has_branched) else GREEN
                    pygame.draw.circle(self.screen, color, center, CELL_SIZE // 6)
                elif terrain == TerrainType.GOAL:
                    if goal_active:
                        flash = int((pygame.time.get_ticks() / 300) % 2)
                        color = (255, 255, 100) if flash else YELLOW
                        pygame.draw.rect(self.screen, color, rect)
                        pygame.draw.rect(self.screen, GREEN, rect, 4)
                    else:
                        pygame.draw.rect(self.screen, YELLOW, rect)
                    text = self.font.render('G', True, BLACK)
                    self.screen.blit(text, text.get_rect(center=rect.center))
                elif terrain == TerrainType.HOLE:
                    filled = any(e.pos == pos and e.carrier == -1
                                 for e in state.entities)
                    if filled:
                        # Filled hole: darker ground + sunken box indicator
                        pygame.draw.rect(self.screen, (160, 120, 60), rect)
                    else:
                        pygame.draw.rect(self.screen, (60, 40, 20), rect)
                        #text = self.font.render('H', True, (150, 100, 50))
                        #self.screen.blit(text, text.get_rect(center=rect.center))
                else:
                    pygame.draw.rect(self.screen, WHITE, rect)

    def draw_entity(self, start_x: int, start_y: int, entity, color: Tuple,
                    state: BranchState):
        """Draw a single entity"""

        if entity.carrier == -1:
            padding = 6
        else:
            padding = 4

        x, y = entity.pos
        rect = pygame.Rect(
            start_x + x * CELL_SIZE + padding,
            start_y + y * CELL_SIZE + padding,
            CELL_SIZE - padding * 2, CELL_SIZE - padding * 2
        )

        # Desaturate color for shadow entities
        is_shadow = state.is_shadow(entity.uid)
        display_color = desaturate_color(color, 0.5) if is_shadow else color

        pygame.draw.rect(self.screen, display_color, rect)
        pygame.draw.rect(self.screen, BLACK, rect, 1)

        text = self.font.render(str(entity.uid), True, WHITE)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_player(self, start_x: int, start_y: int, player, color: Tuple,
                    has_held: bool):
        """Draw the player"""
        px, py = player.pos
        center = (
            start_x + px * CELL_SIZE + CELL_SIZE // 2,
            start_y + py * CELL_SIZE + CELL_SIZE // 2
        )

        dx, dy = player.direction
        arrows = {(0, -1): '^', (0, 1): 'v', (-1, 0): '<', (1, 0): '>'}
        arrow = arrows.get((dx, dy), '^')

        if has_held:
            rect = pygame.Rect(
                start_x + px * CELL_SIZE + 3,
                start_y + py * CELL_SIZE + 3,
                CELL_SIZE - 6, CELL_SIZE - 6
            )
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, BLACK, rect, 2)
        else:
            pygame.draw.circle(self.screen, color, center, CELL_SIZE // 4)

        text = self.arrow_font.render(arrow, True, WHITE)
        self.screen.blit(text, text.get_rect(center=center))

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
                    pygame.draw.rect(self.screen, color, rect, 3)
                else:
                    pygame.draw.rect(self.screen, BLACK, rect, 1)

    def draw_dashed_line(self, start: Tuple[int, int], end: Tuple[int, int],
                         color: Tuple, width: int = 2, dash_length: int = 6,
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
                          color: Tuple, size: int = 16, thickness: int = 5,
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
                          color: Tuple, thickness: int = 1):
        """Draw a static dashed border"""
        x, y = pos
        rect_x = start_x + x * CELL_SIZE
        rect_y = start_y + y * CELL_SIZE

        dash_length = 5
        gap_length = 5

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

            line_color = CYAN

            # Draw flowing dashed lines from other positions to front (slow flow)
            slow_offset = animation_offset * 0.25
            for pos in other_positions:
                other_center = (
                    start_x + pos[0] * CELL_SIZE + CELL_SIZE // 2,
                    start_y + pos[1] * CELL_SIZE + CELL_SIZE // 2
                )
                self.draw_dashed_line(other_center, front_center,
                                      line_color, 2, 8, slow_offset)

            # Draw dashed frames on other shadow positions
            for pos in other_positions:
                self.draw_dashed_frame(start_x, start_y, pos, line_color, 1)

            # Draw pulsing L-shaped lock brackets on front block
            pulse = math.sin(animation_offset / 20) * 0.3 + 0.7
            lock_color = (int(line_color[0] * pulse),
                          int(line_color[1] * pulse),
                          int(line_color[2] * pulse))
            self.draw_lock_corners(start_x, start_y, front_pos, lock_color,
                                   size=16, thickness=5, margin=3)

    def draw_ghost_box(self, start_x: int, start_y: int, pos: Tuple[int, int],
                       uid: int, base_color: Tuple = RED):
        """Draw a semi-transparent ghost box."""
        x, y = pos
        rect = pygame.Rect(
            start_x + x * CELL_SIZE + 4,
            start_y + y * CELL_SIZE + 4,
            CELL_SIZE - 8, CELL_SIZE - 8
        )

        ghost_surface = pygame.Surface((rect.width, rect.height))
        ghost_surface.set_alpha(128)
        ghost_color = desaturate_color(base_color, 0.7)
        ghost_surface.fill(ghost_color)
        self.screen.blit(ghost_surface, (rect.x, rect.y))

        pygame.draw.rect(self.screen, ghost_color, rect, 2)

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

        other_held = {e.uid for e in other.entities if e.carrier == 0}
        focused_held = {e.uid for e in focused.entities if e.carrier == 0}
        inherited = other_held - focused_held

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
                                  inherit_line_color, 2, 8, slow_offset)

            pulse = math.sin(animation_offset / 20) * 0.3 + 0.7
            lock_color = (int(inherit_line_color[0] * pulse),
                          int(inherit_line_color[1] * pulse),
                          int(inherit_line_color[2] * pulse))
            self.draw_lock_corners(start_x, start_y, player_pos, lock_color,
                                   size=16, thickness=5, margin=3)

    def draw_branch(self, state: BranchState, start_x: int, start_y: int,
                    title: str, is_focused: bool, border_color: Tuple,
                    goal_active: bool = False, has_branched: bool = False,
                    animation_offset: int = 0,
                    is_merge_preview: bool = False,
                    main_branch: Optional[BranchState] = None,
                    sub_branch: Optional[BranchState] = None,
                    current_focus: int = 0):
        """Draw a complete branch view"""
        # Title
        title_color = BLACK if is_focused else DARK_GRAY
        self.screen.blit(self.font.render(title, True, title_color),
                         (start_x, start_y - 20))

        # Focus highlight border
        if is_focused:
            highlight_rect = pygame.Rect(
                start_x - 8, start_y - 8,
                GRID_WIDTH + 16, GRID_HEIGHT + 16
            )
            pygame.draw.rect(self.screen, BLUE, highlight_rect, 5)

        # Border
        border_width = 3 if is_focused else 2
        pygame.draw.rect(self.screen, border_color,
                         (start_x, start_y, GRID_WIDTH, GRID_HEIGHT), border_width)

        # Terrain
        self.draw_terrain(start_x, start_y, state, goal_active, has_branched)

        # Entities (non-player, not held)
        for e in state.entities:
            if e.uid != 0 and e.type == EntityType.BOX:
                self.draw_entity(start_x, start_y, e, RED, state)

        # Shadow connections (only on the focused branch)
        if is_focused:
            self.draw_shadow_connections(start_x, start_y, state, animation_offset)

        # Inherited hold hint (only for merge preview)
        if is_merge_preview and main_branch and sub_branch:
            self.draw_inherited_hold_hint(start_x, start_y, state,
                                          main_branch, sub_branch,
                                          current_focus, animation_offset)

        # Player
        has_held = any(e.carrier == 0 for e in state.entities)
        player_color = RED if has_held else BLUE
        if not is_focused:
            player_color = tuple(min(255, c + 80) for c in player_color)
        self.draw_player(start_x, start_y, state.player, player_color, has_held)

        # Grid lines
        self.draw_grid_lines(start_x, start_y, state)

    def draw_overlay(self, text: str, color: Tuple):
        """Draw overlay"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(color)
        self.screen.blit(overlay, (0, 0))

        big_font = pygame.font.Font(None, 72)
        big_text = big_font.render(text, True, YELLOW)
        self.screen.blit(big_text,
                         big_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40)))

        hint = self.font.render("Press F5 to restart", True, WHITE)
        self.screen.blit(hint,
                         hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20)))
