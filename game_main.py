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
    animation_frame = 0

    running = True
    while running:
        clock.tick(60)
        animation_frame += 1

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

                if event.key == pygame.K_z:
                    controller.undo()
                    continue

                if controller.collapsed or controller.victory:
                    continue

                if event.key == pygame.K_v:
                    controller.try_branch()
                elif event.key == pygame.K_c:
                    controller.try_merge()
                elif event.key == pygame.K_TAB:
                    controller.switch_focus()
                elif event.key == pygame.K_x or event.key == pygame.K_SPACE:
                    controller.handle_adaptive_action()

        # Continuous movement
        if not controller.collapsed and not controller.victory and move_cooldown == 0:
            keys = pygame.key.get_pressed()
            direction = None

            if keys[pygame.K_UP] or keys[pygame.K_w]:
                direction = (0, -1)
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                direction = (0, 1)
            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                direction = (-1, 0)
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                direction = (1, 0)

            if direction:
                controller.handle_move(direction)
                move_cooldown = MOVE_DELAY

        if not controller.victory and controller.check_victory():
            # Print solution on victory
            solution = ''.join(controller.input_log)
            print(f"\n=== VICTORY ===")
            print(f"Steps: {len(controller.input_log)}")
            print(f"Solution: {solution}")
            print(f"===============\n")

        # Rendering
        screen.fill((255, 255, 255))

        preview = controller.get_merge_preview()
        goal_active = all(
            any(e.pos == pos for e in preview.entities)
            for pos, t in preview.terrain.items() if t.name == 'SWITCH'
        )
        # Main Branch
        renderer.draw_branch(controller.main_branch,
                             PADDING * 2 + GRID_WIDTH, PADDING + 20,
                             "DIV 0", controller.current_focus == 0, (0, 100, 200),
                             goal_active, controller.has_branched, animation_frame)

        # Merge Preview
        renderer.draw_branch(preview, PADDING, PADDING + 20,
                             "Merge Preview", False, (150, 50, 150),
                             goal_active, controller.has_branched, animation_frame,
                             is_merge_preview=True,
                             main_branch=controller.main_branch,
                             sub_branch=controller.sub_branch,
                             current_focus=controller.current_focus)

        # Sub Branch
        if controller.sub_branch:
            renderer.draw_branch(controller.sub_branch,
                                 PADDING * 3 + GRID_WIDTH * 2, PADDING + 20,
                                 "DIV 1", controller.current_focus == 1, (50, 150, 200),
                                 goal_active, controller.has_branched, animation_frame)

        # Debug info
        renderer.draw_debug_info(
            len(controller.history) - 1,
            controller.current_focus,
            controller.has_branched,
            controller.input_log
        )

        # Overlay
        if controller.collapsed:
            renderer.draw_overlay("FALL DOWN!", (150, 0, 0))
        elif controller.victory:
            renderer.draw_overlay("LEVEL COMPLETE!", (0, 0, 0))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

# ===== 地圖定義 =====
floor_map = '''
#S.G.#
#....#
#HHHH#
#HHHH#
#....#
#..VS#
'''

# Object Map
object_map = '''
......
......
......
......
..BP..
..B...
'''

if __name__ == "__main__":
    run_game(floor_map, object_map)
