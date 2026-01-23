# game_main.py - Main Loop

import pygame
import sys
from map_parser import parse_dual_layer
from game_controller import GameController
from renderer import Renderer, WINDOW_WIDTH, WINDOW_HEIGHT, PADDING, GRID_WIDTH


def run_game(floor_map: str, object_map: str):
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("div - Timeline Puzzle")

    source = parse_dual_layer(floor_map, object_map)
    controller = GameController(source)
    renderer = Renderer(screen)

    clock = pygame.time.Clock()
    move_cooldown = 0
    MOVE_DELAY = 10

    running = True
    while running:
        clock.tick(60)

        if move_cooldown > 0:
            move_cooldown -= 1

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F5:
                    controller.reset()
                    continue

                if controller.collapsed or controller.victory:
                    continue

                if event.key == pygame.K_b:
                    controller.try_branch()
                elif event.key == pygame.K_m:
                    controller.try_merge()
                elif event.key == pygame.K_TAB:
                    controller.switch_focus()
                elif event.key == pygame.K_SPACE:
                    held = any(e.carrier == 0 for e in controller.get_active_branch().entities)
                    if held:
                        controller.handle_drop()
                    else:
                        controller.handle_pickup()

        # Continuous movement
        if not controller.collapsed and not controller.victory and move_cooldown == 0:
            keys = pygame.key.get_pressed()
            direction = None

            if keys[pygame.K_UP]:
                direction = (0, -1)
            elif keys[pygame.K_DOWN]:
                direction = (0, 1)
            elif keys[pygame.K_LEFT]:
                direction = (-1, 0)
            elif keys[pygame.K_RIGHT]:
                direction = (1, 0)

            if direction:
                controller.handle_move(direction)
                move_cooldown = MOVE_DELAY

        controller.check_victory()

        # Rendering
        screen.fill((255, 255, 255))

        preview = controller.get_merge_preview()
        goal_active = all(
            any(e.pos == pos for e in preview.entities)
            for pos, t in preview.terrain.items() if t.name == 'SWITCH'
        )

        # Merge Preview
        renderer.draw_branch(preview, PADDING, PADDING + 20,
                             "Merge Preview", False, (150, 50, 150), goal_active)

        # Main Branch
        renderer.draw_branch(controller.main_branch,
                             PADDING * 2 + GRID_WIDTH, PADDING + 20,
                             "DIV 0", controller.current_focus == 0, (0, 100, 200), goal_active)

        # Sub Branch
        if controller.sub_branch:
            renderer.draw_branch(controller.sub_branch,
                                 PADDING * 3 + GRID_WIDTH * 2, PADDING + 20,
                                 "DIV 1", controller.current_focus == 1, (50, 150, 200), goal_active)

        # Overlay
        if controller.collapsed:
            renderer.draw_overlay("FLOOR COLLAPSED!", (150, 0, 0))
        elif controller.victory:
            renderer.draw_overlay("LEVEL COMPLETE!", (0, 0, 0))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    floor = '''
...G..
......
......
......
...V..
......
'''

    obj = '''
......
......
......
.B....
......
..P...
'''

    run_game(floor, obj)
