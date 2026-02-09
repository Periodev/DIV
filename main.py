# main.py - Game Entry Point
#
# Level selection and game launcher for DIV Timeline Puzzle

from game_window import run_game


# ===== Tutorial Launcher (0-0 ~ 1-5) =====
# All tutorial levels with integrated hint configuration

TUTORIAL_LEVELS = [
    # 0-0: Movement basics (ALL LOCKED - no advanced hints)
    {
        'id': '0-0',
        'name': 'Tutorial - Move',
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
            'movement': False,   # LOCK - basic movement (arrows/WASD shown in base UI)
            'pickup': False,     # LOCK - X key pickup
            'branch': False,     # LOCK - V key split
            'merge': False,      # LOCK - V key merge
            'inherit': False,    # LOCK - C key inherit mode
        }
    },

    # 0-1: Push mechanics (UNLOCK: movement hints)
    {
        'id': '0-1',
        'name': 'Tutorial - Push',
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
            'movement': True,    # UNLOCK - show push/move hints
            'pickup': False,
            'branch': False,
            'merge': False,
            'inherit': False,
        }
    },

    # 0-2: Pickup mechanics (UNLOCK: movement + pickup)
    {
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
            'pickup': True,      # UNLOCK - show X key pickup hint
            'branch': False,
            'merge': False,
            'inherit': False,
        }
    },

    # 0-3: Capacity limits
    {
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
            'branch': False,
            'merge': False,
            'inherit': False,
        }
    },

    # 0-4: Holes
    {
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
            'branch': False,
            'merge': False,
            'inherit': False,
        }
    },

    # 1-1: Timeline split (UNLOCK: branch + merge, LOCK: inherit)
    {
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
            'branch': True,      # UNLOCK - show V key split hint
            'merge': True,       # UNLOCK - show V/M key merge hints
            'inherit': False,    # LOCK - inherit still hidden
        }
    },

    # 1-2: Converge mechanics
    {
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
            'branch': True,
            'merge': True,
            'inherit': False,
        }
    },

    # 1-3: Pass mechanics
    {
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
            'branch': True,
            'merge': True,
            'inherit': False,
        }
    },

    # 1-4: Cross mechanics
    {
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
            'branch': True,
            'merge': True,
            'inherit': False,
        }
    },

    # 1-5: Multiple divergences
    {
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
            'branch': True,
            'merge': True,
            'inherit': False,
        }
    },
]


# ===== Main Levels (2-1+) =====
# Full-featured levels for advanced players

MAIN_LEVELS = [
    # 2-1: Inherit mechanics (ALL UNLOCKED)
    {
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
            'branch': True,
            'merge': True,
            'inherit': True,     # UNLOCK - full feature set
        }
    },

    # 2-2: Bridge mechanics
    {
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
            'branch': True,
            'merge': True,
            'inherit': True,
        }
    },
]


# ===== Launcher Functions =====

def launch_tutorial(level_index: int = 0):
    """Launch tutorial level (0-0 ~ 1-5)."""
    if level_index < 0 or level_index >= len(TUTORIAL_LEVELS):
        print(f"Error: Tutorial level {level_index} not found")
        return

    level = TUTORIAL_LEVELS[level_index]
    print(f"Starting Tutorial: {level['name']} ({level['id']})")
    print(f"Hints enabled: {[k for k, v in level['hints'].items() if v]}")
    run_game(level['floor_map'], level['object_map'], hints=level['hints'])


def launch_level(level_index: int = 0):
    """Launch main level (2-1+)."""
    if level_index < 0 or level_index >= len(MAIN_LEVELS):
        print(f"Error: Level {level_index} not found")
        return

    level = MAIN_LEVELS[level_index]
    print(f"Starting: {level['name']} ({level['id']})")
    run_game(level['floor_map'], level['object_map'], hints=level['hints'])


if __name__ == "__main__":
    # Launch first tutorial level by default
    launch_tutorial(0)
