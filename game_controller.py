# game_controller.py - Game Controller

from timeline_system import BranchState, Timeline, Physics, TerrainType, init_branch_from_source, LevelSource
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
        return Timeline.converge(self.main_branch, self.sub_branch, self.current_focus)

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

        merged = Timeline.converge(self.main_branch, self.sub_branch, self.current_focus)

        # Check collapse
        if Physics.check_collapse(merged):
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
        """Handle movement input"""
        active = self.get_active_branch()

        # Turn direction
        if active.player.direction != direction:
            active.player.direction = direction
            return True

        # Move
        if GameLogic.can_move(active, direction):
            GameLogic.execute_move(active, direction)

            if Physics.check_collapse(active):
                self.collapsed = True
                return False
            if Physics.check_fall(active):
                self.collapsed = True
                return False

            return True
        return False

    def handle_pickup(self) -> bool:
        """Handle pickup action"""
        active = self.get_active_branch()
        result = GameLogic.try_pickup(active)

        if result and Physics.check_collapse(active):
            self.collapsed = True
            return False
        if result and Physics.check_fall(active):
            self.collapsed = True
            return False

        return result

    def handle_drop(self) -> bool:
        """Handle drop action"""
        active = self.get_active_branch()
        result = GameLogic.try_drop(active)

        if result and Physics.check_collapse(active):
            self.collapsed = True
            return False
        if result and Physics.check_fall(active):
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
