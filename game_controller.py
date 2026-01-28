# game_controller.py - Game Controller

from timeline_system import BranchState, Timeline, Physics, PhysicsResult, TerrainType, EntityType, init_branch_from_source, LevelSource
from game_logic import GameLogic
from typing import Optional


class GameController:
    def __init__(self, source: LevelSource):
        self.source = source
        self.main_branch: Optional[BranchState] = None
        self.sub_branch: Optional[BranchState] = None
        self.current_focus = 0  # 0=main, 1=sub
        self.has_branched = False

        self.collapsed = False
        self.victory = False

        self.reset()

    def reset(self):
        """Reset level"""
        initial = init_branch_from_source(self.source)
        self.main_branch = initial
        self.sub_branch = None
        self.current_focus = 0
        self.has_branched = False
        self.collapsed = False
        self.victory = False

    def get_active_branch(self) -> BranchState:
        """Get the currently controlled branch"""
        if self.current_focus == 0:
            return self.main_branch
        return self.sub_branch

    def get_merge_preview(self) -> BranchState:
        """Get merge preview"""
        if not self.has_branched:
            return self.main_branch

        focused, other = (self.main_branch, self.sub_branch) if self.current_focus == 0 else (self.sub_branch, self.main_branch)
        merged = Timeline.converge(focused, other)
        preview = merged.copy()
        Timeline.settle_carried(preview)
        return preview

    def try_branch(self) -> bool:
        """Attempt to create a branch"""
        if self.has_branched:
            return False

        active = self.get_active_branch()
        if active.terrain.get(active.player.pos) != TerrainType.BRANCH:
            return False

        self.sub_branch = Timeline.diverge(self.main_branch)
        self.has_branched = True
        return True

    def try_merge(self) -> bool:
        """Attempt to merge branches"""
        if not self.has_branched:
            return False

        focused, other = (self.main_branch, self.sub_branch) if self.current_focus == 0 else (self.sub_branch, self.main_branch)
        merged = Timeline.converge(focused, other)

        # Settle: held boxes must converge immediately
        Timeline.settle_carried(merged)

        # Physics step
        if Physics.step(merged) != PhysicsResult.OK:
            self.collapsed = True
            return False

        self.main_branch = merged
        self.sub_branch = None
        self.has_branched = False
        self.current_focus = 0
        return True

    def switch_focus(self):
        """Switch controlled branch"""
        if self.has_branched:
            self.current_focus = 1 - self.current_focus

    def handle_move(self, direction: tuple) -> bool:
        """Handle movement input.

        Object-adaptive turning:
        - When facing a box: first press turns to face it, second press moves/pushes
        - When holding item: same two-step behavior (turn, then move)
        - Otherwise: single press turns and moves (fluid exploration)

        This design slows the player down when interacting with important objects
        (boxes), preventing accidental pushes while keeping movement fluid in open areas.
        """
        active = self.get_active_branch()
        px, py = active.player.pos
        dx, dy = direction
        target_pos = (px + dx, py + dy)

        # Check if there's a grounded box at target position (including shadows)
        has_box_ahead = any(
            e.type == EntityType.BOX and e.pos == target_pos and Physics.grounded(e)
            for e in active.entities
        )

        is_holding = bool(active.get_held_items())

        # Two-step turning: when holding OR when facing a box
        if is_holding or has_box_ahead:
            if active.player.direction != direction:
                active.player.direction = direction
                return True
        else:
            # Open area: set direction immediately, then try to move
            active.player.direction = direction

        # Attempt move
        if GameLogic.can_move(active, direction):
            GameLogic.execute_move(active, direction)

            if Physics.step(active) != PhysicsResult.OK:
                self.collapsed = True
                return False

            return True
        return False

    def handle_pickup(self) -> bool:
        """Handle pickup action"""
        active = self.get_active_branch()
        result = GameLogic.try_pickup(active)

        if result and Physics.step(active) != PhysicsResult.OK:
            self.collapsed = True
            return False

        return result

    def handle_drop(self) -> bool:
        """Handle drop action"""
        active = self.get_active_branch()
        result = GameLogic.try_drop(active)

        if result and Physics.step(active) != PhysicsResult.OK:
            self.collapsed = True
            return False

        return result

    def check_victory(self) -> bool:
        """Check victory conditions"""
        if self.has_branched:
            return False

        preview = self.get_merge_preview()

        # All switches activated
        switches_ok = all(
            Physics.weight_at(pos, preview) > 0
            for pos, t in preview.terrain.items()
            if t == TerrainType.SWITCH
        )

        # Player on goal
        goal_ok = preview.terrain.get(preview.player.pos) == TerrainType.GOAL

        self.victory = switches_ok and goal_ok
        return self.victory
