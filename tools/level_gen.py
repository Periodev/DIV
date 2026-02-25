"""
tools/level_gen.py — Random DIV level generator.

Produces level_dict compatible with solver_core.solve() and map_parser.parse_dual_layer().
Top-down 2D puzzle; no vertical gravity. Only physics: H tiles swallow entities.

Usage:
    from tools.level_gen import generate_level
    ld = generate_level(width=5, height=5, n_switches=2, n_charge=1, seed=42)
    # ld is None on failure, else dict with 'floor_map', 'object_map', 'hints'
"""

import random
from collections import deque

# ---------------------------------------------------------------------------
# Tile symbols
# ---------------------------------------------------------------------------
WALL    = '#'
FLOOR   = '.'
SWITCH  = 'S'
GOAL    = 'G'
HOLE    = 'H'
NOCARRY = 'c'

CHARGE_TILES = ('v', 'V', 'x', 'X')   # 1/2/3/4 charges

# Tiles that are walkable (player/box can stand on them)
PASSABLE = frozenset({FLOOR, SWITCH, GOAL, NOCARRY, 'v', 'V', 'x', 'X'})


# ---------------------------------------------------------------------------
# Grid helpers
# ---------------------------------------------------------------------------

def _neighbors4(x, y, w, h):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            yield nx, ny


def _bfs_distances(grid, sx, sy, w, h):
    """BFS from (sx,sy); returns dict {pos: distance} for all reachable passable cells."""
    dist = {(sx, sy): 0}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for nx, ny in _neighbors4(x, y, w, h):
            if (nx, ny) not in dist and grid[ny][nx] in PASSABLE:
                dist[(nx, ny)] = dist[(x, y)] + 1
                q.append((nx, ny))
    return dist


def _reachable_set(grid, sx, sy, w, h):
    return set(_bfs_distances(grid, sx, sy, w, h).keys())


def _dead_ends(grid, w, h, exclude=()):
    """Passable cells with exactly 1 passable neighbour (natural cul-de-sacs)."""
    exclude = set(exclude)
    ends = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] not in PASSABLE or (x, y) in exclude:
                continue
            n = sum(1 for nx, ny in _neighbors4(x, y, w, h) if grid[ny][nx] in PASSABLE)
            if n == 1:
                ends.append((x, y))
    return ends


# ---------------------------------------------------------------------------
# Carver (random walk)
# ---------------------------------------------------------------------------

def _carve(grid, w, h, rng, min_cells=8, target_ratio=0.60, border_walls=True):
    """
    Random walk from centre, turning walls into floor.
    border_walls=True: keeps the outermost ring as walls (larger grids).
    border_walls=False: allows all cells, needed for small grids (3×3, 4×4).
    """
    cx, cy = w // 2, h // 2
    grid[cy][cx] = FLOOR
    carved = {(cx, cy)}
    if border_walls:
        interior = max(1, (w - 2) * (h - 2))
        x_lo, x_hi, y_lo, y_hi = 1, w - 2, 1, h - 2
    else:
        interior = w * h
        x_lo, x_hi, y_lo, y_hi = 0, w - 1, 0, h - 1
    target = max(min_cells, int(interior * target_ratio))
    x, y = cx, cy
    steps = 0
    max_steps = w * h * 80

    while len(carved) < target and steps < max_steps:
        steps += 1
        dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
        nx, ny = x + dx, y + dy
        if x_lo <= nx <= x_hi and y_lo <= ny <= y_hi:
            if grid[ny][nx] == WALL:
                grid[ny][nx] = FLOOR
                carved.add((nx, ny))
            x, y = nx, ny

    return carved


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_level(
    width: int = 5,
    height: int = 5,
    n_switches: int = 2,
    n_boxes: int = 1,
    n_charge: int = 1,
    charge_type: str = 'v',
    n_nocarry: int = 0,
    n_holes: int = 0,
    min_pg_dist: int = None,       # minimum P→G BFS distance; default = (w+h)//3
    seed: int = None,
    max_attempts: int = 400,
) -> dict | None:
    """
    Generate a random level_dict.

    Parameters
    ----------
    width, height    Grid dimensions (borders always walls).
    n_switches       Number of S tiles.  Goal only unlocks when all are active.
    n_boxes          Number of boxes (B in object map).
    n_charge         Number of charge tiles (v/V/x/X).
    charge_type      Which charge tile symbol to use ('v'=1ch … 'X'=4ch).
    n_nocarry        Number of no-carry (c) tiles.
    n_holes          Number of hole (H) tiles.
    min_pg_dist      Minimum BFS steps from P to G (ensures non-trivial level).
    seed             RNG seed for reproducibility.
    max_attempts     Retries before giving up (returns None).

    Returns
    -------
    dict with keys: 'id', 'floor_map', 'object_map', 'hints'
    or None if no valid layout found.
    """
    if charge_type not in CHARGE_TILES:
        raise ValueError(f"charge_type must be one of {CHARGE_TILES}")

    rng = random.Random(seed)
    if min_pg_dist is None:
        min_pg_dist = (width + height) // 3

    # Minimum passable cells needed
    min_walk = 2 + n_switches + n_boxes + n_charge + n_nocarry + n_holes + 2

    for attempt in range(max_attempts):
        # ── 1. Init all-wall grid ──────────────────────────────────────────
        grid = [[WALL] * width for _ in range(height)]

        # ── 2. Carve walkable region ───────────────────────────────────────
        use_border_walls = (width >= 5 and height >= 5)
        _carve(grid, width, height, rng,
               min_cells=min_walk, border_walls=use_border_walls)
        walkable = [(x, y) for y in range(height) for x in range(width)
                    if grid[y][x] == FLOOR]

        if len(walkable) < min_walk:
            continue

        # ── 3. Pick P position (random) ───────────────────────────────────
        rng.shuffle(walkable)
        p_pos = walkable[0]

        # ── 4. Pick G position: furthest reachable cell from P ────────────
        dist_from_p = _bfs_distances(grid, p_pos[0], p_pos[1], width, height)
        if len(dist_from_p) < min_walk:
            continue  # too disconnected

        # Among the farthest cells pick one at or beyond min_pg_dist
        far_cells = [(d, pos) for pos, d in dist_from_p.items()
                     if d >= min_pg_dist and pos != p_pos]
        if not far_cells:
            continue
        far_cells.sort(reverse=True)
        # Pick randomly among top 25%
        top_n = max(1, len(far_cells) // 4)
        _, g_pos = rng.choice(far_cells[:top_n])

        grid[g_pos[1]][g_pos[0]] = GOAL

        # ── 5. Remaining walkable (exclude P and G) ────────────────────────
        used = {p_pos, g_pos}
        remaining = [c for c in walkable if c not in used]
        rng.shuffle(remaining)

        needed = n_switches + n_nocarry + n_charge + n_holes + n_boxes
        if len(remaining) < needed:
            continue

        idx = 0

        # ── 6. Place switches ──────────────────────────────────────────────
        switch_positions = []
        for _ in range(n_switches):
            grid[remaining[idx][1]][remaining[idx][0]] = SWITCH
            switch_positions.append(remaining[idx])
            used.add(remaining[idx])
            idx += 1

        # ── 7. Place no-carry tiles ────────────────────────────────────────
        for _ in range(n_nocarry):
            grid[remaining[idx][1]][remaining[idx][0]] = NOCARRY
            used.add(remaining[idx])
            idx += 1

        # ── 8. Place charge tiles — prefer dead ends ───────────────────────
        dead = [c for c in _dead_ends(grid, width, height, exclude=used)
                if c not in used]
        rng.shuffle(dead)
        charge_pool = dead + [c for c in remaining[idx:] if c not in used]
        charge_positions = []
        for i in range(n_charge):
            if i < len(charge_pool):
                cx, cy = charge_pool[i]
                grid[cy][cx] = charge_type
                charge_positions.append((cx, cy))
                used.add((cx, cy))
            else:
                break  # ran out of candidates
        if len(charge_positions) < n_charge:
            continue

        # Advance idx past cells now used by charge tiles that came from remaining
        while idx < len(remaining) and remaining[idx] in used:
            idx += 1

        # ── 9. Place holes ─────────────────────────────────────────────────
        for _ in range(n_holes):
            if idx < len(remaining):
                grid[remaining[idx][1]][remaining[idx][0]] = HOLE
                used.add(remaining[idx])
                idx += 1

        # ── 10. Place boxes ────────────────────────────────────────────────
        box_positions = []
        for _ in range(n_boxes):
            while idx < len(remaining) and remaining[idx] in used:
                idx += 1
            if idx < len(remaining):
                box_positions.append(remaining[idx])
                used.add(remaining[idx])
                idx += 1
        if len(box_positions) < n_boxes:
            continue

        # ── 11. Connectivity: P must reach G and all switches ──────────────
        reach = _reachable_set(grid, p_pos[0], p_pos[1], width, height)
        if g_pos not in reach:
            continue
        if any(s not in reach for s in switch_positions):
            continue

        # ── 12. Serialise to map strings ───────────────────────────────────
        floor_rows = [''.join(row) for row in grid]
        floor_map = '\n'.join(floor_rows)

        obj_rows = [['.' for _ in range(width)] for _ in range(height)]
        obj_rows[p_pos[1]][p_pos[0]] = 'P'
        for bx, by in box_positions:
            obj_rows[by][bx] = 'B'
        object_map = '\n'.join(''.join(row) for row in obj_rows)

        # ── 13. Build hints ────────────────────────────────────────────────
        has_branch = n_charge > 0
        hints = {
            'diverge':  has_branch,
            'converge': has_branch,
            'pickup':   n_boxes > 0,
            'fetch':    has_branch and n_boxes > 0,
        }

        return {
            'id':         f'gen_s{seed}_a{attempt}',
            'name':       f'gen {width}x{height} sw{n_switches} ch{n_charge}',
            'floor_map':  floor_map,
            'object_map': object_map,
            'hints':      hints,
            # metadata for pipeline use
            '_seed':      seed,
            '_attempt':   attempt,
            '_p_pos':     p_pos,
            '_g_pos':     g_pos,
            '_switches':  switch_positions,
            '_charges':   charge_positions,
            '_boxes':     box_positions,
        }

    return None  # exhausted attempts


# ---------------------------------------------------------------------------
# Pretty-print helper
# ---------------------------------------------------------------------------

def print_level(ld: dict) -> None:
    """Print a generated level_dict in human-readable form."""
    print(f"ID: {ld['id']}  ({ld['name']})")
    print("Floor:")
    for row in ld['floor_map'].split('\n'):
        print(f"  {row}")
    print("Objects:")
    for row in ld['object_map'].split('\n'):
        print(f"  {row}")
    meta_keys = ('_p_pos', '_g_pos', '_switches', '_charges', '_boxes')
    for k in meta_keys:
        if k in ld:
            print(f"  {k[1:]}: {ld[k]}")


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    print(f"Generating with seed={seed} ...\n")
    ld = generate_level(
        width=5, height=5,
        n_switches=2,
        n_boxes=1,
        n_charge=1,
        charge_type='v',
        seed=seed,
    )
    if ld is None:
        print("Generation failed.")
    else:
        print_level(ld)
        print()

        # Quick parse check
        from map_parser import parse_dual_layer
        src = parse_dual_layer(ld['floor_map'], ld['object_map'])
        print(f"Parsed OK — grid_size={src.grid_size}, "
              f"entities={len(src.entity_definitions)}, "
              f"terrain_tiles={len(src.terrain)}")
