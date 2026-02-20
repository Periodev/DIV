# timeline_system.py - Complete Timeline System

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Set, Tuple, Optional
from enum import Enum

Position = Tuple[int, int]

class EntityType(Enum):
    PLAYER = "player"
    BOX = "box"

class TerrainType(Enum):
    FLOOR = "."
    WALL = "#"
    SWITCH = "S"
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
    fused_from: Optional[FrozenSet[int]] = None  # uids of absorbed entities

# ===== Branch State =====
class BranchState:
    def __init__(self):
        self.entities: List[Entity] = []
        self.terrain: Dict[Position, TerrainType] = {}
        self.grid_size: int = 0
        self.next_uid: int = 0

    def copy(self) -> 'BranchState':
        """Deep copy"""
        new_state = BranchState()
        new_state.terrain = self.terrain.copy()
        new_state.grid_size = self.grid_size
        new_state.next_uid = self.next_uid
        new_state.entities = [
            Entity(
                uid=e.uid,
                type=e.type,
                pos=e.pos,
                collision=e.collision,
                weight=e.weight,
                z=e.z,
                holder=e.holder,
                direction=e.direction,
                fused_from=e.fused_from
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

    def get_non_held_instances(self, uid: int) -> List[Entity]:
        """Get non-held instances of a uid that will converge when merged.

        Returns instances that are grounded (z=0) or in-hole (z=-1).
        Used for convergence hints and merge preview.
        """
        return [e for e in self.entities
                if e.uid == uid and e.z <= 0 and e.holder is None]

    def is_shadow(self, uid: int) -> bool:
        """Check if entity is in shadow state (multiple positions or fusion paradox).

        Fusion paradox: after merging two branches where only one performed a fusion,
        both the fusion entity AND its source uids coexist. The fusion IS the shadow
        combined form of its sources, so all involved entities count as shadow.
        """
        instances = self.get_entities_by_uid(uid)
        if not instances:
            return False
        # Standard shadow: same uid at multiple (pos, z) locations
        positions = {(e.pos, e.z) for e in instances}
        if len(positions) > 1:
            return True

        # Fusion paradox ①: this entity is a fusion AND at least one source still exists
        entity = instances[0]
        if entity.fused_from:
            if any(e.uid in entity.fused_from for e in self.entities):
                return True

        # Fusion paradox ②: a fusion entity exists that has absorbed this uid
        if any(e.fused_from and uid in e.fused_from
               for e in self.entities if e.uid != uid):
            return True

        return False

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

    def switch_activated(self, pos: Position) -> bool:
        """Check if a switch is activated by a grounded box at pos."""
        return any(e.type == EntityType.BOX
                   and e.pos == pos
                   and Physics.grounded(e)
                   for e in self.entities)

    def all_switches_activated(self) -> bool:
        """Check if all switches are activated by boxes."""
        return all(self.switch_activated(pos)
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
    def diverge(branch: BranchState) -> Tuple['BranchState', 'BranchState']:
        """Diverge: returns (main, sub) pair.

        Fusion entities are inseparable and carried into both branches as-is.
        """
        main = branch.copy()
        sub = branch.copy()
        return main, sub

    @staticmethod
    def _copy_entity(e: Entity) -> Entity:
        """Create a copy of an entity."""
        return Entity(
            uid=e.uid, type=e.type, pos=e.pos,
            collision=e.collision, weight=e.weight,
            z=e.z, holder=e.holder, direction=e.direction,
            fused_from=e.fused_from
        )

    @staticmethod
    def try_fuse(state: BranchState, pos: Position) -> bool:
        """Check if multiple shadow entities overlap at pos; if so, fuse them into one.

        Returns True if fusion occurred.
        """
        # Find all distinct uids with an instance at pos (z=0, grounded)
        shadow_uids_at_pos = [
            e.uid for e in state.entities
            if e.uid != 0
            and e.type == EntityType.BOX
            and e.pos == pos
            and Physics.grounded(e)
        ]
        # Deduplicate while preserving order
        seen = set()
        unique_shadow_uids = []
        for uid in shadow_uids_at_pos:
            if uid not in seen:
                seen.add(uid)
                unique_shadow_uids.append(uid)

        if len(unique_shadow_uids) < 2:
            return False

        # Don't create a new fusion if the entities at this pos are already in a
        # fusion-paradox relationship (one uid is absorbed inside another uid's fused_from).
        # e.g. uid5(fused_from={1,2}) + uid1 at same pos → paradox, not a new fusion.
        uids_set = set(unique_shadow_uids)
        entities_at_pos = [e for e in state.entities if e.uid in uids_set]
        already_absorbed = Timeline._absorbed_uid_closure(entities_at_pos)
        if already_absorbed & uids_set:
            return False

        # Remove all instances of each fusing uid
        fused_from = frozenset(unique_shadow_uids)
        state.entities = [
            e for e in state.entities
            if e.uid not in seen
        ]

        # Create fusion entity
        new_uid = state.next_uid
        state.next_uid += 1
        fusion = Entity(
            uid=new_uid,
            type=EntityType.BOX,
            pos=pos,
            collision=1,
            # Preserve physical consistency when fusing 2+ shadow uids.
            weight=len(fused_from),
            z=0,
            fused_from=fused_from
        )
        state.entities.append(fusion)
        return True

    @staticmethod
    def _entity_priority(e: Entity) -> tuple:
        """Priority for dedup: held > grounded > in-hole."""
        return (e.holder is not None, e.z)

    @staticmethod
    def _absorbed_uid_closure(entities: List[Entity]) -> Set[int]:
        """Collect all uids absorbed by any fusion entity (transitively)."""
        fused_map: Dict[int, Set[int]] = {}
        seeds: List[int] = []

        for e in entities:
            if not e.fused_from:
                continue
            fused_map.setdefault(e.uid, set()).update(e.fused_from)
            seeds.extend(e.fused_from)

        absorbed: Set[int] = set()
        stack = list(seeds)
        while stack:
            uid = stack.pop()
            if uid in absorbed:
                continue
            absorbed.add(uid)
            for child_uid in fused_map.get(uid, ()):
                if child_uid not in absorbed:
                    stack.append(child_uid)
        return absorbed

    @staticmethod
    def converge(main: BranchState, sub: BranchState) -> BranchState:
        """
        Merge two branches.
        main: the focused branch (player taken from here)
        sub: the non-focused branch
        Caller must determine focus and pass in correct order.

        Non-focused branch's held items are dropped at sub player's position.
        """
        result = BranchState()
        result.terrain = main.terrain.copy()
        result.grid_size = main.grid_size
        result.next_uid = max(main.next_uid, sub.next_uid)

        # Find items held by sub (non-focused) branch that need to be dropped
        sub_held_uids = set(sub.get_held_items())

        # Collect all non-player entities from both branches
        all_entities = [e for e in main.entities if e.uid != 0] + \
                       [e for e in sub.entities if e.uid != 0]

        # Group by (uid, pos, z) - include z so underground and grounded instances are kept separate.
        # Fusion paradox: if one branch fused boxes that still exist in the other branch,
        # all involved entities are preserved as shadow (resolved later via X action).
        by_uid_pos: Dict[Tuple[int, Position, int], List[Entity]] = {}
        for e in all_entities:
            key = (e.uid, e.pos, e.z)
            by_uid_pos.setdefault(key, []).append(e)

        # Pick best instance per (uid, pos, z) group
        for instances in by_uid_pos.values():
            best = max(instances, key=Timeline._entity_priority)
            copied = Timeline._copy_entity(best)

            # Drop sub's held items at sub player's position
            # Only drop if the box was held by sub (at sub's position)
            if copied.uid in sub_held_uids and copied.holder == 0 and copied.pos == sub.player.pos:
                copied.holder = None
                copied.z = 0
                copied.collision = 1
                # pos is already sub.player.pos

            result.entities.append(copied)

        # Remove source instances co-located with their fusion entity.
        # e.g. uid3(1+2)@pos3 + uid1@pos3 → remove uid1@pos3 (already represented by fusion).
        # Sources at other positions are kept as paradox shadows for X-resolution.
        fusions = [e for e in result.entities if e.fused_from]
        if fusions:
            co_located = {(uid, fusion.pos)
                          for fusion in fusions
                          for uid in fusion.fused_from}
            result.entities = [e for e in result.entities
                               if (e.uid, e.pos) not in co_located]

        # Add player from main (focused) branch at position 0
        result.entities.insert(0, Timeline._copy_entity(main.player))

        return result

    @staticmethod
    def merge_normal(main: BranchState, sub: BranchState) -> BranchState:
        """Full normal merge: converge + settle carried items."""
        merged = Timeline.converge(main, sub)
        Timeline.settle_carried(merged)
        return merged

    @staticmethod
    def merge_inherit(main: BranchState, sub: BranchState, inherit_uids: Set[int]) -> BranchState:
        """Full inherit merge: converge + mark inherit items + settle."""
        merged = Timeline.converge(main, sub)
        if inherit_uids:
            for uid in inherit_uids:
                for e in merged.entities:
                    if e.uid == uid:
                        e.holder = 0
        Timeline.settle_carried(merged)
        return merged

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
        # Priority 2: best instance at target_pos (by _entity_priority, e.g. z=0 over z=-1)
        elif target_pos:
            at_pos_instances = [e for e in instances if e.pos == target_pos]
            if at_pos_instances:
                target = max(at_pos_instances, key=Timeline._entity_priority)
            else:
                target = instances[0]
        # Priority 3: first instance
        else:
            target = instances[0]

        state.entities = [e for e in state.entities if e.uid != target_uid]
        state.entities.append(target)
        return target

    @staticmethod
    def resolve_fusion_toward_fusion(state: BranchState, fusion_uid: int):
        """Resolve fusion paradox by keeping the fusion, removing its source entities."""
        absorbed = Timeline._absorbed_uid_closure(state.entities)
        state.entities = [e for e in state.entities if e.uid not in absorbed]

    @staticmethod
    def resolve_fusion_toward_sources(state: BranchState, source_uid: int):
        """Resolve fusion paradox by keeping the sources, removing the fusion entity."""
        fusion = next(
            (e for e in state.entities
             if e.fused_from and source_uid in e.fused_from),
            None
        )
        if fusion is None:
            return
        state.entities = [e for e in state.entities if e.uid != fusion.uid]

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

    state.next_uid = source.next_uid
    return state
