# main.py - Game Entry Point
#
# Level selection and game launcher for DIV Timeline Puzzle

from game_window import run_game


# ===== Level Definitions =====
# Format: L{world}_{stage} corresponding to id '{world}-{stage}'

# Tutorial World 0: Basic Mechanics
L0_0 = {
    'id': '0-0',
    'name': 'Tutorial - Move',
    'floor_map': '''
.####.
..##..
......
.#..#.
.####.
.####G
''',
    'object_map': '''
......
......
......
......
......
P.....
''',
    'hints': {
        'movement': False,   # LOCK - Tab switching (teaching basic WASD only)
        'pickup': False,     # LOCK - X key pickup
        'diverge': False,    # LOCK - V key split
        'merge': False,      # LOCK - V/M key merge
        'inherit': False,    # LOCK - C key inherit mode
    }
}

L0_1 = {
    'id': '0-1',
    'name': 'Tutorial - Push',
    'floor_map': '''
#G...#
#.##..
#.#...
#....#
#.####
#.####
''',
    'object_map': '''
......
.B....
....B.
..B...
.B....
.P....
''',
    'hints': {
        'movement': True,    # UNLOCK - Tab switching unlocked
        'pickup': False,
        'diverge': False,
        'merge': False,
        'inherit': False,
    }
}

L0_2 = {
    'id': '0-2',
    'name': 'Tutorial - Goal',
    'floor_map': '''
#S..##
...###
.#####
.##S.G
..##..
#....#
''',
    'object_map': '''
..BP..
......
......
....B.
......
......
''',
    'hints': {
        'movement': True,
        'pickup': False,
        'diverge': False,
        'merge': False,
        'inherit': False,
    }
}

L0_3 = {
    'id': '0-2',
    'name': 'Tutorial - Pick',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,      # UNLOCK - X key pickup
        'diverge': False,
        'merge': False,
        'inherit': False,
    }
}

L0_4 = {
    'id': '0-3',
    'name': 'Tutorial - Limit',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': False,
        'merge': False,
        'inherit': False,
    }
}


L0_5 = {
    'id': '0-4',
    'name': 'Tutorial - Hole',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': False,
        'merge': False,
        'inherit': False,
    }
}

# Tutorial World 1: Timeline Mechanics
L1_1 = {
    'id': '1-1',
    'name': 'Tutorial - Split',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,     # UNLOCK - V key split
        'merge': True,       # UNLOCK - V/M key merge
        'inherit': False,    # LOCK - inherit still hidden
    }
}

L1_2 = {
    'id': '1-2',
    'name': 'Tutorial - Converge',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': False,
    }
}

L1_3 = {
    'id': '1-3',
    'name': 'Tutorial - Pass',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': False,
    }
}

L1_4 = {
    'id': '1-4',
    'name': 'Tutorial - Cross',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': False,
    }
}

L1_5 = {
    'id': '1-5',
    'name': 'Tutorial - Divergences',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': False,
    }
}

# Main World 2: Advanced Mechanics
L2_1 = {
    'id': '2-1',
    'name': 'Level - Inherit',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': True,     # UNLOCK - full feature set
    }
}

L2_2 = {
    'id': '2-2',
    'name': 'Level - Bridge',
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
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': True,
    }
}


# ===== Level Collections =====

TUTORIAL_LEVELS = [
    L0_0, L0_1, L0_2, L0_3, L0_4,  # World 0: Basic mechanics
    L1_1, L1_2, L1_3, L1_4, L1_5,  # World 1: Timeline mechanics
]

MAIN_LEVELS = [
    L2_1, L2_2,  # World 2: Advanced mechanics
]


# ===== Launcher Functions =====

def launch(level):
    """Launch a level directly from level variable (e.g., launch(L0_0))."""
    if not isinstance(level, dict) or 'id' not in level:
        print(f"Error: Invalid level. Expected level dict (e.g., L0_0), got {type(level)}")
        return

    print(f"Starting: {level['name']} ({level['id']})")
    print(f"Hints enabled: {[k for k, v in level['hints'].items() if v]}")
    run_game(level['floor_map'], level['object_map'], hints=level['hints'])


def launch_tutorial(level_index: int = 0):
    """Launch tutorial level by index (0-9)."""
    if level_index < 0 or level_index >= len(TUTORIAL_LEVELS):
        print(f"Error: Tutorial level {level_index} not found")
        return

    level = TUTORIAL_LEVELS[level_index]
    launch(level)


def launch_level(level_index: int = 0):
    """Launch main level by index."""
    if level_index < 0 or level_index >= len(MAIN_LEVELS):
        print(f"Error: Level {level_index} not found")
        return

    level = MAIN_LEVELS[level_index]
    launch(level)


def launch_by_id(level_id: str):
    """Launch level by ID (e.g., '0-0', '1-3', '2-1')."""
    # Build lookup dictionary
    all_levels = {level['id']: level for level in TUTORIAL_LEVELS + MAIN_LEVELS}

    if level_id not in all_levels:
        print(f"Error: Level {level_id} not found")
        print(f"Available levels: {', '.join(sorted(all_levels.keys()))}")
        return

    level = all_levels[level_id]
    print(f"Starting: {level['name']} ({level['id']})")
    print(f"Hints enabled: {[k for k, v in level['hints'].items() if v]}")
    run_game(level['floor_map'], level['object_map'], hints=level['hints'])


if __name__ == "__main__":
    # Method 1: Launch by level variable (recommended)
    launch(L0_2)

    # Method 2: Launch by index
    # launch_tutorial(0)  # L0_0
    # launch_tutorial(5)  # L1_1

    # Method 3: Launch by ID
    # launch_by_id('0-0')
    # launch_by_id('1-3')
