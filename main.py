# main.py - Game Entry Point
#
# Level selection and game launcher for DIV Timeline Puzzle

from game_window import run_game


# ===== Level Definitions =====

LEVEL_1 = {
    'name': 'Tutorial',
    'floor_map': '''
######
#c####
#vccG#
####S#
######
######
''',
    'object_map': '''
......
......
.PB...
......
......
......
'''
}

# Future levels can be added here:
# LEVEL_2 = {...}
# LEVEL_3 = {...}

LEVELS = [LEVEL_1]


def select_level(level_index: int = 0):
    """Launch a specific level."""
    if level_index < 0 or level_index >= len(LEVELS):
        print(f"Error: Level {level_index} not found")
        return

    level = LEVELS[level_index]
    print(f"Starting: {level['name']}")
    run_game(level['floor_map'], level['object_map'])


if __name__ == "__main__":
    # Launch first level by default
    select_level(0)
