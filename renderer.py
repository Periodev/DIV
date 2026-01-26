# renderer.py - Pygame Rendering System

import pygame
from timeline_system import BranchState, TerrainType, EntityType
from typing import Tuple

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
                     goal_active: bool = False):
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
                    pygame.draw.circle(self.screen, GREEN, center, CELL_SIZE // 6)
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
                    pygame.draw.rect(self.screen, (60, 40, 20), rect)
                    text = self.font.render('H', True, (150, 100, 50))
                    self.screen.blit(text, text.get_rect(center=rect.center))
                else:
                    pygame.draw.rect(self.screen, WHITE, rect)

    def draw_entity(self, start_x: int, start_y: int, entity, color: Tuple):
        """Draw a single entity"""
        x, y = entity.pos
        rect = pygame.Rect(
            start_x + x * CELL_SIZE + 4,
            start_y + y * CELL_SIZE + 4,
            CELL_SIZE - 8, CELL_SIZE - 8
        )

        pygame.draw.rect(self.screen, color, rect)
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
                start_x + px * CELL_SIZE + 8,
                start_y + py * CELL_SIZE + 8,
                CELL_SIZE - 16, CELL_SIZE - 16
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

    def draw_branch(self, state: BranchState, start_x: int, start_y: int,
                    title: str, is_focused: bool, border_color: Tuple,
                    goal_active: bool = False):
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
        self.draw_terrain(start_x, start_y, state, goal_active)

        # Entities (non-player, not held)
        for e in state.entities:
            if e.uid != 0 and e.carrier is None and e.type == EntityType.BOX:
                self.draw_entity(start_x, start_y, e, RED)

        # Player
        has_held = any(e.carrier == 0 for e in state.entities)
        player_color = PURPLE if has_held else BLUE
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
