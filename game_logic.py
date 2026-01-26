# game_logic.py - Game Rules and Actions

from timeline_system import BranchState, Physics, Entity, TerrainType, EntityType, Timeline
from typing import Literal, Optional


class GameLogic:
    @staticmethod
    def can_move(state: BranchState, direction: tuple) -> bool:
        """Check if movement is possible"""
        px, py = state.player.pos
        dx, dy = direction
        new_pos = (px + dx, py + dy)

        # Out of bounds
        x, y = new_pos
        if not (0 <= x < state.grid_size and 0 <= y < state.grid_size):
            return False

        # Wall
        if state.terrain.get(new_pos) == TerrainType.WALL:
            return False

        # Collision check
        collision = Physics.collision_at(new_pos, state)
        print(f"[MOVE] collision={collision}")

        # Unfilled HOLE blocks player
        if collision < 0:
            return False

        if collision > 0:
            # Check if any blocking entity is a shadow (can't push shadows)
            pushable = [e for e in state.entities
                        if e.pos == new_pos and e.collision > 0 and Physics.grounded(e)]
            for e in pushable:
                if state.is_shadow(e.uid):
                    return False

            # Attempt push
            push_pos = (new_pos[0] + dx, new_pos[1] + dy)
            if not (0 <= push_pos[0] < state.grid_size and 0 <= push_pos[1] < state.grid_size):
                return False
            if state.terrain.get(push_pos) == TerrainType.WALL:
                return False
            if Physics.collision_at(push_pos, state) > 0:
                return False

        return True

    @staticmethod
    def execute_move(state: BranchState, direction: tuple):
        """Execute movement (including box pushing)"""
        px, py = state.player.pos
        dx, dy = direction
        new_pos = (px + dx, py + dy)

        # Push boxes (only free entities, not terrain-contained)
        entities_at_new = [e for e in state.entities
                           if e.pos == new_pos and e.collision > 0 and Physics.grounded(e)]
        if entities_at_new:
            push_pos = (new_pos[0] + dx, new_pos[1] + dy)
            for e in entities_at_new:
                e.pos = push_pos
            # Check if pushed into unfilled HOLE → trigger fill
            for e in entities_at_new:
                Physics.trigger_fill(state, e, push_pos)

        # Move player
        state.player.pos = new_pos
        state.player.direction = direction

        # Update carried object positions
        for e in state.entities:
            if e.carrier == 0:
                e.pos = new_pos

    @staticmethod
    def try_pickup(state: BranchState) -> bool:
        """Pick up object in front of player"""
        px, py = state.player.pos
        dx, dy = state.player.direction
        front_pos = (px + dx, py + dy)

        # Find pickable objects in front (only BOX)
        target = next((e for e in state.entities 
                            if e.pos == front_pos 
                            and e.type == EntityType.BOX 
                            and Physics.grounded(e)), None)
        if target is None:
            return False

        target = Timeline.converge_one(state, target.uid)

        target.carrier = 0
        target.collision = 0
        target.pos = state.player.pos
 
        return True

    @staticmethod
    def try_drop(state: BranchState) -> bool:
        """Drop held object"""
        px, py = state.player.pos
        dx, dy = state.player.direction
        front_pos = (px + dx, py + dy)

        # Check if holding any object
        held = [e for e in state.entities if e.carrier == 0]
        if not held:
            return False

        # Check target position
        fx, fy = front_pos
        if not (0 <= fx < state.grid_size and 0 <= fy < state.grid_size):
            return False
        if state.terrain.get(front_pos) == TerrainType.WALL:
            return False
        if Physics.collision_at(front_pos, state) > 0:
            return False

        # Drop
        for e in held:
            e.carrier = None
            e.collision = 1
            e.pos = front_pos

        # Check if dropped into unfilled HOLE → trigger fill
        for e in held:
            Physics.trigger_fill(state, e, front_pos)

        return True
