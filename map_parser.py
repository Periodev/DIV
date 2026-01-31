"""
div - Dual-layer Map Parser
Symbol definitions:
  Floor: . (floor) ' ' (void) # (wall) S (switch) w (weight-limit 1) W (weight-limit 2) V (branch point) G (goal) H (hole)
  Object: . (empty) P (player) B (box)

All IDs are auto-generated in left-to-right, top-to-bottom order.
"""

from timeline_system import LevelSource, EntityType, TerrainType


def parse_dual_layer(floor_map_str, object_map_str) -> LevelSource:
    """
    Parse dual-layer map strings and return a LevelSource.
    All symbols are single characters; IDs are auto-generated.
    """
    floor_lines = [line.rstrip() for line in floor_map_str.strip().split('\n') if line.strip()]
    object_lines = [line.rstrip() for line in object_map_str.strip().split('\n') if line.strip()]

    if len(floor_lines) != len(object_lines):
        raise ValueError("Floor and object maps must have same height")

    # Calculate grid_size
    max_width = max(len(line) for line in floor_lines) if floor_lines else 0
    grid_size = max(len(floor_lines), max_width)

    terrain = {}
    entity_definitions = {}
    uid = 0

    # Parse floor layer -> terrain
    for y, line in enumerate(floor_lines):
        for x, char in enumerate(line):
            pos = (x, y)
            if char == '#' or char == ' ':
                terrain[pos] = TerrainType.WALL
            elif char == 'v':
                terrain[pos] = TerrainType.BRANCH1
            elif char == 'V':
                terrain[pos] = TerrainType.BRANCH2
            elif char == 'x':
                terrain[pos] = TerrainType.BRANCH3
            elif char == 'X':
                terrain[pos] = TerrainType.BRANCH4
            elif char == 'G':
                terrain[pos] = TerrainType.GOAL
            elif char == 'H':
                terrain[pos] = TerrainType.HOLE
            elif char == 'S':
                terrain[pos] = TerrainType.SWITCH
            elif char == 'w':
                terrain[pos] = TerrainType.WEIGHT1
            elif char == 'W':
                terrain[pos] = TerrainType.WEIGHT2
            # '.' is not added to terrain (default FLOOR)

    # Parse object layer -> entity_definitions
    for y, line in enumerate(object_lines):
        for x, char in enumerate(line):
            if char == 'P':
                entity_definitions[0] = (EntityType.PLAYER, (x, y))
            elif char == 'B':
                uid += 1
                entity_definitions[uid] = (EntityType.BOX, (x, y))

    # Validate required elements
    if 0 not in entity_definitions:
        raise ValueError("Player start position (P) not found")
    if TerrainType.GOAL not in terrain.values():
        raise ValueError("Goal position (G) not found")

    return LevelSource(
        grid_size=grid_size,
        terrain=terrain,
        entity_definitions=entity_definitions,
        next_uid=uid + 1
    )


def parse_level(level_id, name, title, floor_map_str, object_map_str, hints=None):
    """
    Convenience function: parse map and attach metadata.

    Args:
        level_id: Level number
        name: Level name
        title: Display title
        floor_map_str: Floor layer map string
        object_map_str: Object layer map string
        hints: Hint message dict (optional)

    Returns:
        Dict with LevelSource and metadata
    """
    source = parse_dual_layer(floor_map_str, object_map_str)

    return {
        'id': level_id,
        'name': name,
        'title': title,
        'source': source,
        'hints': hints or {
            'initial': '',
            'branched': '',
            'goal_active': '',
            'victory': ''
        }
    }
