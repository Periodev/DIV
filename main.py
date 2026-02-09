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
    },
    'tutorial': {
        'title': '關卡 0-0：移動',
        'items': [
            '使用 W/A/S/D 或方向鍵移動角色',
            '角色會以藍色圓圈顯示，黑色箭頭顯示方向',
            '黑色區域是牆壁，無法通過',
            '黃色的 Goal 是目標點',
            '走到閃爍的 Goal 即可過關',
            '',
            '提示：按住方向鍵可以持續移動',
        ]
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
    },
    'tutorial': {
        'title': '關卡 0-1：推動',
        'items': [
            '標記數字的有色方形是方塊',
            '面向方塊按移動可以推動方塊',
            '若方塊後方有牆壁或其它方塊，就無法推動',
            '利用推動來清出通往目標的路徑',
                        '',
            '提示：如果沒有面對方塊，朝方塊按下方向鍵會原地轉向',
        ]
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
    },
    'tutorial': {
        'title': '關卡 0-2：目標',
        'items': [
            '灰色地磚是開關',
            '將方塊推到開關後會壓下開關變綠色',
            '黃色的 Goal 是目標點',
            '當所有開關都壓下，Goal就會啟動',
        ]
    }
}

L0_3 = {
    'id': '0-3',
    'name': 'Tutorial - Pick',
    'floor_map': '''
#....#
..##..
.#####
.#####
..##.G
#....#
''',
    'object_map': '''
......
.B..BP
......
......
.B..B.
......
''',
    'hints': {
        'movement': True,
        'pickup': True,      # UNLOCK - X key pickup
        'diverge': False,
        'merge': False,
        'inherit': False,
    },
    'tutorial': {
        'title': '關卡 0-3：拾取與放下',
        'items': [
            '按 X 或空白鍵可以拾取面前的方塊',
            '拾起方塊後，角色會變為方塊的顏色，可以攜帶方塊移動',
            '再按一次 X 或空白鍵可以放下方塊',
            '方塊會放置在角色面前的格子',
            '',
            '提示：可拾取的方塊，會出現提示 拾取',
            '提示：可放置方塊的地板，會出現提示 放下',
            '提示：攜帶方塊時會變精確移動模式，須轉動方向，再往面對方向移動',

        ]
    }
}

L0_4 = {
    'id': '0-4',
    'name': 'Tutorial - Limit',
    'floor_map': '''
cS####
cc####
c.####
cc####
S.ccG#
cc.cS#
''',
    'object_map': '''
P.....
B.....
......
......
.BB...
......
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': False,
        'merge': False,
        'inherit': False,
    },
    'tutorial': {
        'title': '關卡 0-4：限制',
        'items': [
            '紅色地板是「禁止攜帶」區域',
            '角色或方塊可以在紅色地板上移動，但無法攜帶方塊',
            '站在不可攜帶區撿取方塊會失敗，只允許推動',
            '如果攜帶方塊接近會被阻檔',
            '',
            '提示：拾取無效時不會出現可拾取的提示',

        ]
    }
}


L0_5 = {
    'id': '0-5',
    'name': 'Tutorial - Hole',
    'floor_map': '''
..##..
H.##..
H.HH..
HH.H.H
H.##HH
H.##HG
''',
    'object_map': '''
P.....
....BB
.B....
......
......
.B....
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': False,
        'merge': False,
        'inherit': False,
    },
    'tutorial': {
        'title': '關卡 0-5：坑洞',
        'items': [
            '棕色是坑洞，角色和方塊都無法通過',
            '將方塊推入或放入洞中可以填補洞口',
            '填補後的洞可以正常通過',
            '利用方塊填洞來開闢道路',
            '注意：方塊推入洞後無法取回',
        ]
    }
}

# Tutorial World 1: Timeline Mechanics
L1_1 = {
    'id': '1-1',
    'name': 'Tutorial - Split',
    'floor_map': '''
######
#....#
#S..S#
##.v##
##G.##
######
''',
    'object_map': '''
......
...P..
..B...
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
    },
    'tutorial': {
        'title': '關卡 1-1：分裂',
        'items': [
            '綠色的點是 分裂點',
            '站在分裂點上，再按 V 鍵可以分裂，複製兩個平行空間',
            '按 Tab 鍵可以切換視角',
            '按 M 鍵可以預覽合併後的狀態',
            '確認無誤後按 V 鍵執行合併',
            '合併後，方塊會保持壓住開關的狀態',
            '',
            '提示：只要各個空間累計按下所有開關，終點就會亮',
            '提示：M預覽模式可以Tab切換視角',
            '提示：一般模式可按 V 鍵快速合併',
            '提示：分裂點使用次數有限，若失敗可按 Z取消 或 F5重試',

        ]
    }
}

L1_2 = {
    'id': '1-2',
    'name': 'Tutorial - Converge',
    'floor_map': '''
######
######
vccccG
######
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
    },
    'tutorial': {
        'title': '關卡 1-2：收束',
        'items': [
            '分裂後的方塊，如果在不同位置合併，會留下殘影',
            '殘影不可推動，並且會阻擋玩家移動',
            '對著面前的殘影可使用收束，將變回實體並回收其它殘影',
            '',
            '提示：可收束的殘影會出現提示 收束，並有虛線連結到目標',
            '提示：合併會以當前視角的玩家位置為基準',
            '提示：安排適當位置收束，讓玩家穿過方塊',
            

        ]
    }
}

L1_3 = {
    'id': '1-3',
    'name': 'Pass',
    'floor_map': '''
######
###.##
vcccG#
###S##
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
    },
    'tutorial': {
        'title': '關卡 1-3：接力',
        'items': [
            '提示：在適當位置收束，讓方塊轉向',

        ]
    }
}

L1_4 = {
    'id': '1-4',
    'name': 'Cross',
    'floor_map': '''
######
###c##
#vcccG
###c##
###S##
###v##
''',
    'object_map': '''
......
......
...B..
...P..
......
......
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': False,
    },
    'tutorial': {
        'title': '關卡 1-4：十字路口',
        'items': [
        ]
    }
}

L1_5 = {
    'id': '1-5',
    'name': 'Tutorial - Divergences',
    'floor_map': '''
######
#S####
#G.cV#
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
......''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': False,
    },
    'tutorial': {
        'title': '關卡 1-5：分歧',
        'items': [
            '分裂點的圈數代表可使用次數',

        ]
    }
}

# Main World 2: Advanced Mechanics
L2_1 = {
    'id': '2-1',
    'name': 'Tutorial - Inherit',
    'floor_map': '''
######
##SG##
##HH##
##.v##
##..##
######
''',
    'object_map': '''
......
......
......
......
..BP..
......
''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': True,     # UNLOCK - full feature set
    },
    'tutorial': {
        'title': '關卡 2-1：繼承',
        'items': [
            '按 C 鍵可以切換「繼承模式」',
            '開啟繼承模式後，按 M 鍵預覽合併',
            '會顯示綠色提示：可以繼承物品',
            '在繼承模式下按 V 鍵執行繼承合併',
            '合併後會保留兩條時間線的物品',
            '這個關卡需要繼承方塊來填補洞口',
        ]
    }
}

L2_2 = {
    'id': '2-2',
    'name': 'Bridge',
    'floor_map': '''
##.G##
##HH##
##HH##
##HH##
##..##
##.v##
''',
    'object_map': '''
......
......
......
......
..BP..
..B...''',
    'hints': {
        'movement': True,
        'pickup': True,
        'diverge': True,
        'merge': True,
        'inherit': True,
    },
    'tutorial': {
        'title': '關卡 2-2：橋樑',
        'items': [
            '目標前方有多個洞需要填補',
            '地圖上只有兩個方塊',
            '利用繼承合併來複製方塊',
            '一條時間線拿方塊填洞',
            '另一條時間線保留方塊',
            '繼承合併後兩個方塊都會保留',
            '重複此過程來獲得足夠的方塊',
        ]
    }
}


# ===== Level Collections =====

TUTORIAL_LEVELS = [
    L0_0, L0_1, L0_2, L0_3, L0_4, L0_5,  # World 0: Basic mechanics
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

    # Get tutorial if available
    tutorial = level.get('tutorial')
    if tutorial:
        print(f"Tutorial available: Press H to view")

    run_game(level['floor_map'], level['object_map'],
             hints=level['hints'], tutorial=tutorial)


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
    launch(L1_5)  # Test tutorial overlay

    # Method 2: Launch by index
    # launch_tutorial(0)  # L0_0
    # launch_tutorial(5)  # L1_1

    # Method 3: Launch by ID
    # launch_by_id('0-0')
    # launch_by_id('1-3')
