# timeline_system.py - Complete Timeline System

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum

Position = Tuple[int, int]

class EntityType(Enum):
    PLAYER = "player"
    BOX = "box"

class TerrainType(Enum):
    FLOOR = "."
    WALL = "#"
    SWITCH = "S"
    WEIGHT1 = "w"
    WEIGHT2 = "W"
    NO_CARRY = "c"
    BRANCH1 = "v"  # 1 use remaining
    BRANCH2 = "V"  # 2 uses remaining
    BRANCH3 = "x"  # 3 uses remaining
    BRANCH4 = "X"  # 4 uses remaining
    GOAL = "G"
    HOLE = "H"

class PhysicsResult(Enum):
    OK = 0
    FALL = 1

# ===== Static Configuration =====
@dataclass
class LevelSource:
    """Raw configuration imported from map_parser"""
    grid_size: int
    terrain: Dict[Position, TerrainType]
    entity_definitions: Dict[int, Tuple[EntityType, Position]]
    # {0: (PLAYER, (2,5)), 1: (BOX, (1,1)), ...}
    next_uid: int

# ===== Runtime Entity =====
@dataclass
class Entity:
    """0th-order: existence (uid) + 1st-order: physical properties"""
    uid: int  # 0 = player
    type: EntityType
    pos: Position
    collision: int = 1  # collision volume
    weight: int = 1
    z: int = 0  # height layer: -1=underground, 0=ground, 1=held
    holder: Optional[int] = None  # uid of holder (None=not held)
    direction: Position = (0, 1)  # player-exclusive

# ===== Branch State =====
class BranchState:
    def __init__(self):
        self.entities: List[Entity] = []
        self.terrain: Dict[Position, TerrainType] = {}
        self.grid_size: int = 0

    def copy(self) -> 'BranchState':
        """Deep copy"""
        new_state = BranchState()
        new_state.terrain = self.terrain.copy()
        new_state.grid_size = self.grid_size
        new_state.entities = [
            Entity(
                uid=e.uid,
                type=e.type,
                pos=e.pos,
                collision=e.collision,
                weight=e.weight,
                z=e.z,
                holder=e.holder,
                direction=e.direction
            )
            for e in self.entities
        ]
        return new_state

    @property
    def player(self) -> Entity:
        """entities[0] = player"""
        return self.entities[0]

    def get_entities_by_uid(self, uid: int) -> List[Entity]:
        """Get all instances with the same uid (for shadow detection)"""
        return [e for e in self.entities if e.uid == uid]

    def is_shadow(self, uid: int) -> bool:
        """Check if entity is in shadow state (multiple positions)"""
        instances = self.get_entities_by_uid(uid)
        if not instances:
            return False
        positions = {e.pos for e in instances}
        return len(positions) > 1

    def get_held_items(self) -> List[int]:
        """Get uids of all items held by player (holder == 0).
        Returns empty list if player is empty-handed."""
        return [e.uid for e in self.entities if e.holder == 0]

    def is_hole_filled(self, pos: Position) -> bool:
        """Check if a hole at pos is filled (has underground entity)."""
        return any(e.pos == pos and e.z == -1 for e in self.entities)

    def find_box_at(self, pos: Position) -> Optional['Entity']:
        """Find a grounded box at pos (pickup/interaction target)."""
        return next((e for e in self.entities
                     if e.pos == pos
                     and e.type == EntityType.BOX
                     and Physics.grounded(e)), None)

    def get_blocking_entities_at(self, pos: Position) -> List['Entity']:
        """Get grounded entities with collision at pos (pushable objects)."""
        return [e for e in self.entities
                if e.pos == pos
                and e.collision > 0
                and Physics.grounded(e)]

    def has_box_at(self, pos: Position) -> bool:
        """Check if a grounded box exists at pos."""
        return any(e.type == EntityType.BOX
                   and e.pos == pos
                   and Physics.grounded(e)
                   for e in self.entities)

    def all_switches_activated(self) -> bool:
        """Check if all switches have weight on them."""
        return all(Physics.weight_at(pos, self) > 0
                   for pos, t in self.terrain.items()
                   if t == TerrainType.SWITCH)

    def sum_ground_collision_at(self, pos: Position) -> int:
        """Total collision volume of ground-level entities at pos."""
        return sum(e.collision for e in self.entities
                   if e.pos == pos and e.z >= 0)

    def sum_weight_at(self, pos: Position) -> int:
        """Total weight of all entities at pos."""
        return sum(e.weight for e in self.entities if e.pos == pos)

# ===== Timeline (Pure Functions) =====
class Timeline:
    @staticmethod
    def diverge(branch: BranchState) -> BranchState:
        """Diverge: deep copy"""
        return branch.copy()

    @staticmethod
    def _copy_entity(e: Entity) -> Entity:
        """Create a copy of an entity."""
        return Entity(
            uid=e.uid, type=e.type, pos=e.pos,
            collision=e.collision, weight=e.weight,
            z=e.z, holder=e.holder, direction=e.direction
        )

    @staticmethod
    def _entity_priority(e: Entity) -> tuple:
        """Priority for dedup: held > grounded > in-hole."""
        return (e.holder is not None, e.z)

    @staticmethod
    def converge(main: BranchState, sub: BranchState) -> BranchState:
        """
        Merge two branches.
        main: the focused branch (player taken from here)
        sub: the non-focused branch
        Caller must determine focus and pass in correct order.
        """
        result = BranchState()
        result.terrain = main.terrain.copy()
        result.grid_size = main.grid_size

        # Find uids that must drop: sub holding something AND main also holding something
        main_held_uids = set(main.get_held_items())
        sub_held_uids = set(sub.get_held_items())
        # Only drop sub's held items if main is also holding (can't hold two different items)
        drop_uids = (sub_held_uids - main_held_uids) if main_held_uids else set()

        # Collect all non-player entities from both branches
        all_entities = [e for e in main.entities if e.uid != 0] + \
                       [e for e in sub.entities if e.uid != 0]

        # Group by (uid, pos)
        by_uid_pos: Dict[Tuple[int, Position], List[Entity]] = {}
        for e in all_entities:
            key = (e.uid, e.pos)
            by_uid_pos.setdefault(key, []).append(e)

        # Pick best instance per (uid, pos) group
        for instances in by_uid_pos.values():
            best = max(instances, key=Timeline._entity_priority)
            copied = Timeline._copy_entity(best)

            # Sub's held entities drop at sub player's position (only if main also holding)
            if copied.uid in drop_uids and copied.holder == 0:
                copied.holder = None
                copied.z = 0
                copied.collision = 1
                copied.pos = sub.player.pos

            result.entities.append(copied)

        # Add player from main (focused) branch at position 0
        result.entities.insert(0, Timeline._copy_entity(main.player))

        return result

    @staticmethod
    def converge_one(state: BranchState, target_uid: int, target_pos: Position = None) -> Entity:
        """Collapse all instances of a uid into one.

        Priority: held > target_pos > first instance
        """
        instances = [e for e in state.entities if e.uid == target_uid]
        if not instances:
            return None

        # Priority 1: held instance
        held = next((e for e in instances if e.holder == 0), None)
        if held:
            target = held
        # Priority 2: instance at target_pos
        elif target_pos:
            at_pos = next((e for e in instances if e.pos == target_pos), None)
            target = at_pos if at_pos else instances[0]
        # Priority 3: first instance
        else:
            target = instances[0]

        state.entities = [e for e in state.entities if e.uid != target_uid]
        state.entities.append(target)
        return target

    @staticmethod
    def settle_carried(state: BranchState):
        """After merge, converge all shadow instances of held entities"""
        held_uids = set(state.get_held_items())
        if not held_uids:
            return
        for uid in held_uids:
            target = Timeline.converge_one(state, uid)
            target.z = 1
            target.holder = 0
            target.collision = 0
            target.pos = state.player.pos

# ===== Physics =====
class Physics:
    @staticmethod
    def collision_at(pos: Position, state: BranchState) -> int:
        """Total collision volume at position (terrain base + entity sum)"""

        if state.terrain.get(pos) == TerrainType.HOLE:
            # Fusion: filled hole = floor; filling entities don't count
            filled = state.is_hole_filled(pos)
            terrain_base = 0 if filled else -1
            entity_sum = state.sum_ground_collision_at(pos)
        elif state.terrain.get(pos) == TerrainType.WALL:
            terrain_base = 255
            entity_sum = 0
        elif not Physics.in_bound(pos, state):
            terrain_base = 255
            entity_sum = 0
        else:
            terrain_base = 0
            entity_sum = sum(e.collision for e in state.entities if e.pos == pos)

        return terrain_base + entity_sum

    @staticmethod
    def weight_at(pos: Position, state: BranchState) -> int:
        """Total weight at position"""
        return state.sum_weight_at(pos)

    @staticmethod
    def check_fall(state: BranchState) -> bool:
        """Ground can't support player: net collision < player's own contribution"""
        return Physics.collision_at(state.player.pos, state) < state.player.collision

    @staticmethod
    def trigger_fill(state: BranchState, box: 'Entity', pos: Position):
        """Fill an unfilled HOLE at pos with the given box"""
        if state.terrain.get(pos) != TerrainType.HOLE:
            return
        if state.is_hole_filled(pos):
            return  # already filled
        box.z = -1  # underground layer

    @staticmethod
    def settle_holes(state: 'BranchState'):
        """Check all grounded boxes — if sitting on an unfilled hole, fill it."""
        for e in state.entities:
            if e.type == EntityType.BOX and Physics.grounded(e):
                Physics.trigger_fill(state, e, e.pos)

    @staticmethod
    def grounded(entity: 'Entity'):
        return entity.z == 0

    @staticmethod
    def effective_capacity(state: BranchState, at_pos: Position = None) -> int:
        """Calculate effective carrying capacity at a position.

        Args:
            state: Current game state
            at_pos: Position to check (None = player's current position)

        Returns:
            Effective capacity (0 = cannot carry, 1 = can carry one item)
        """
        base_capacity = 1

        # Default to player's current position
        pos = at_pos if at_pos is not None else state.player.pos
        terrain = state.terrain.get(pos, TerrainType.FLOOR)

        # NO_CARRY terrain reduces capacity to 0
        if terrain == TerrainType.NO_CARRY:
            return 0

        return base_capacity

    @staticmethod
    def in_bound(pos: Position, state: BranchState):
        return (0 <= pos[0] < state.grid_size and 0 <= pos[1] < state.grid_size)

    @staticmethod
    def step(state: BranchState) -> 'PhysicsResult':
        """Run physics until stable, return failure mode if any."""
        # 1. Settle holes (loop until no change for chain reactions)
        while True:
            changed = False
            for e in state.entities:
                if e.type == EntityType.BOX and Physics.grounded(e):
                    if state.terrain.get(e.pos) == TerrainType.HOLE:
                        if not state.is_hole_filled(e.pos):
                            e.z = -1
                            changed = True
            if not changed:
                break

        # 2. Check fall only (collapse checks removed)
        if Physics.check_fall(state):
            return PhysicsResult.FALL

        return PhysicsResult.OK

# ===== Initialization Utility =====
def init_branch_from_source(source: LevelSource) -> BranchState:
    """Create initial BranchState from LevelSource"""
    state = BranchState()
    state.terrain = source.terrain.copy()
    state.grid_size = source.grid_size
    # Instantiate all entity definitions
    for uid in sorted(source.entity_definitions.keys()):
        etype, pos = source.entity_definitions[uid]
        state.entities.append(Entity(
            uid=uid,
            type=etype,
            pos=pos,
            collision=1,
            weight=1
        ))

    return state
