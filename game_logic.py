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

        # Collision check
        collision = Physics.collision_at(new_pos, state)
        print(f"[MOVE] collision={collision}")

        # Unfilled HOLE blocks player
        if collision < 0:
            return False

        # boundary
        if collision >= 255:
            return False

        if collision > 0:
            # Check if any blocking entity is a shadow (can't push shadows)
            pushable = state.get_blocking_entities_at(new_pos)
            for e in pushable:
                if state.is_shadow(e.uid):
                    return False

            # Attempt push
            push_pos = (new_pos[0] + dx, new_pos[1] + dy)

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
        entities_at_new = state.get_blocking_entities_at(new_pos)
        if entities_at_new:
            push_pos = (new_pos[0] + dx, new_pos[1] + dy)
            for e in entities_at_new:
                e.pos = push_pos

        # Move player
        state.player.pos = new_pos
        state.player.direction = direction

        # Update carried object positions
        for e in state.entities:
            if e.holder == 0:
                e.pos = new_pos

    @staticmethod
    def try_pickup(state: BranchState) -> bool:
        """Pick up object in front of player"""
        px, py = state.player.pos
        dx, dy = state.player.direction
        front_pos = (px + dx, py + dy)

        # Find pickable objects in front (only BOX)
        target = state.find_box_at(front_pos)
        if target is None:
            return False

        target = Timeline.converge_one(state, target.uid)

        target.z = 1
        target.holder = 0
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
        held = [e for e in state.entities if e.holder == 0]
        if not held:
            return False

        if Physics.collision_at(front_pos, state) > 0:
            return False

        # Drop
        for e in held:
            e.z = 0
            e.holder = None
            e.collision = 1
            e.pos = front_pos

        return True
