# game_main.py - Main Loop

import pygame
import sys
from map_parser import parse_dual_layer
from game_controller import GameController
from renderer import Renderer, WINDOW_WIDTH, WINDOW_HEIGHT
from presentation_model import ViewModelBuilder


def run_game(floor_map: str, object_map: str,
              tutorial_title: str = None, tutorial_items: list = None):
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("div - Timeline Puzzle")

    source = parse_dual_layer(floor_map, object_map)
    controller = GameController(source)
    renderer = Renderer(screen)

    # Default tutorial if none provided
    if tutorial_title is None:
        tutorial_title = "0-3 Pick"
    if tutorial_items is None:
        tutorial_items = [
            "靠近並面對方塊，按X或space可拾取方塊",
            "手上有方塊時，再按X或space可放下到前方一格",
            "舉著方塊會變為精確移動模式，只能朝正前方移動",
            "舉方塊時，可以推動正前方一個方塊",
        ]

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
                if event.key == pygame.K_F5 or event.key == pygame.K_r:
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

        # Unified physics check (settle holes, detect collapse/fall)
        if not controller.collapsed and not controller.victory:
            controller.update_physics()

        if not controller.victory and controller.check_victory():
            # Print solution on victory
            solution = ''.join(controller.input_log)
            print(f"\n=== VICTORY ===")
            print(f"Steps: {len(controller.input_log)}")
            print(f"Solution: {solution}")
            print(f"===============\n")

        # Rendering - Layer 2 transforms state to visual spec, Layer 3 draws it
        frame_spec = ViewModelBuilder.build(controller, animation_frame, tutorial_title, tutorial_items)
        renderer.draw_frame(frame_spec)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

# ===== 地圖定義 =====
floor_map = '''
##SG##
##..##
##HH##
##wv##
##..##
######
'''

# Object Map
object_map = '''
......
......
......
......
..BP..
......
'''


if __name__ == "__main__":
    run_game(floor_map, object_map)
