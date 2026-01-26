# game_logic.py - Game Rules and Actions

from timeline_system import BranchState, Physics, Entity, TerrainType, EntityType
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

        if collision > 0:
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

        # Push boxes
        entities_at_new = [e for e in state.entities if e.pos == new_pos and e.collision > 0]
        if entities_at_new:
            push_pos = (new_pos[0] + dx, new_pos[1] + dy)
            for e in entities_at_new:
                e.pos = push_pos

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

        # Find pickable objects in front
        targets = [e for e in state.entities
                   if e.pos == front_pos and e.uid != 0 and e.carrier is None]

        if not targets:
            return False

        # Pick up all instances of the same uid
        target_uids = {e.uid for e in targets}
        for e in state.entities:
            if e.uid in target_uids:
                e.carrier = 0
                e.collision = 0
                e.pos = state.player.pos

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
        if state.terrain.get(front_pos) == TerrainType.WALL:
            return False
        if Physics.collision_at(front_pos, state) > 0:
            return False

        # Drop
        for e in held:
            e.carrier = None
            e.collision = 1
            e.pos = front_pos

        return True
