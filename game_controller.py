# game_controller.py - Game Controller

from dataclasses import dataclass
from typing import Optional, List
from timeline_system import BranchState, Timeline, Physics, PhysicsResult, TerrainType, EntityType, init_branch_from_source, LevelSource
from game_logic import GameLogic


@dataclass
class GameSnapshot:
    """Snapshot of game state for undo functionality."""
    main_branch: BranchState
    sub_branch: Optional[BranchState]
    current_focus: int
    has_branched: bool


class GameController:
    def __init__(self, source: LevelSource):
        self.source = source
        self.main_branch: Optional[BranchState] = None
        self.sub_branch: Optional[BranchState] = None
        self.current_focus = 0  # 0=main, 1=sub
        self.has_branched = False

        self.collapsed = False
        self.victory = False

        self.history: List[GameSnapshot] = []
        self.input_log: List[str] = []  # Key sequence for replay/validation

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
        self.history.clear()
        self.input_log.clear()
        self._save_snapshot()  # Save initial state

    def _save_snapshot(self):
        """Save current state to history."""
        snapshot = GameSnapshot(
            main_branch=self.main_branch.copy(),
            sub_branch=self.sub_branch.copy() if self.sub_branch else None,
            current_focus=self.current_focus,
            has_branched=self.has_branched
        )
        self.history.append(snapshot)

    def undo(self) -> bool:
        """Restore previous state. Returns True if successful."""
        if len(self.history) <= 1:
            return False  # Keep at least initial state

        self.history.pop()  # Remove current state
        if self.input_log:
            self.input_log.pop()  # Remove last input
        snapshot = self.history[-1]  # Get previous state

        self.main_branch = snapshot.main_branch.copy()
        self.sub_branch = snapshot.sub_branch.copy() if snapshot.sub_branch else None
        self.current_focus = snapshot.current_focus
        self.has_branched = snapshot.has_branched
        self.collapsed = False
        self.victory = False

        return True

    def get_active_branch(self) -> BranchState:
        """Get the currently controlled branch"""
        if self.current_focus == 0:
            return self.main_branch
        return self.sub_branch

    def update_physics(self):
        """Unified physics check. Call once per frame in the main loop.

        Settles holes and checks for fall conditions.
        The failed state is already saved in history, so the player
        sees the failure frame before the overlay appears.
        """
        active = self.get_active_branch()
        result = Physics.step(active)

        # Simplified: only check FALL
        if result == PhysicsResult.FALL:
            self.collapsed = True

    def get_merge_preview(self) -> BranchState:
        """Get merge preview"""
        if not self.has_branched:
            return self.main_branch

        focused, other = (self.main_branch, self.sub_branch) if self.current_focus == 0 else (self.sub_branch, self.main_branch)
        merged = Timeline.converge(focused, other)
        preview = merged.copy()
        Timeline.settle_carried(preview)
        return preview

    # Branch point usage: decrement after use
    BRANCH_DECREMENT = {
        TerrainType.BRANCH4: TerrainType.BRANCH3,
        TerrainType.BRANCH3: TerrainType.BRANCH2,
        TerrainType.BRANCH2: TerrainType.BRANCH1,
        TerrainType.BRANCH1: TerrainType.FLOOR,
    }

    def try_branch(self) -> bool:
        """Attempt to create a branch"""
        if self.has_branched:
            return False

        active = self.get_active_branch()
        terrain = active.terrain.get(active.player.pos)

        # Check if on a branch point (BRANCH1-4)
        if terrain not in self.BRANCH_DECREMENT:
            return False

        # Decrement branch uses in main_branch (before diverge)
        new_terrain = self.BRANCH_DECREMENT[terrain]
        self.main_branch.terrain[active.player.pos] = new_terrain

        self.sub_branch = Timeline.diverge(self.main_branch)
        self.has_branched = True
        self.input_log.append('V')
        self._save_snapshot()
        return True

    def try_merge(self) -> bool:
        """Attempt to merge branches"""
        if not self.has_branched:
            return False

        focused, other = (self.main_branch, self.sub_branch) if self.current_focus == 0 else (self.sub_branch, self.main_branch)
        merged = Timeline.converge(focused, other)

        # Settle: held boxes must converge immediately
        Timeline.settle_carried(merged)

        self.main_branch = merged
        self.sub_branch = None
        self.has_branched = False
        self.current_focus = 0
        self.input_log.append('C')
        self._save_snapshot()
        return True

    def switch_focus(self) -> bool:
        """Switch controlled branch. Returns True if switched."""
        if not self.has_branched:
            return False
        self.current_focus = 1 - self.current_focus
        self.input_log.append('T')
        self._save_snapshot()
        return True

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
        has_box_ahead = active.has_box_at(target_pos)

        is_holding = bool(active.get_held_items())

        # Direction to key mapping
        dir_key = {(0, -1): 'U', (0, 1): 'D', (-1, 0): 'L', (1, 0): 'R'}[direction]

        # Two-step turning: when holding OR when facing a box
        if is_holding or has_box_ahead:
            if active.player.direction != direction:
                active.player.direction = direction
                self.input_log.append(dir_key)
                self._save_snapshot()
                return True
        else:
            # Open area: set direction immediately, then try to move
            active.player.direction = direction

        # Attempt move
        if GameLogic.can_move(active, direction):
            GameLogic.execute_move(active, direction)
            self.input_log.append(dir_key)
            self._save_snapshot()
            return True
        return False

    def handle_pickup(self) -> bool:
        """Handle pickup action"""
        active = self.get_active_branch()
        result = GameLogic.try_pickup(active)
        if result:
            self.input_log.append('P')
            self._save_snapshot()
        return result

    def handle_drop(self) -> bool:
        """Handle drop action"""
        active = self.get_active_branch()
        result = GameLogic.try_drop(active)
        if result:
            self.input_log.append('O')
            self._save_snapshot()
        return result

    def handle_adaptive_action(self) -> bool:
        """Adaptive X action:
        - If holding: drop (same as Space)
        - If facing shadow in active branch: converge only (stay on ground)
        - If facing solid: pickup
        """
        active = self.get_active_branch()

        # If holding, drop
        if active.get_held_items():
            return self.handle_drop()

        # Check what's in front
        px, py = active.player.pos
        dx, dy = active.player.direction
        front_pos = (px + dx, py + dy)

        # Find grounded box at front position
        target = active.find_box_at(front_pos)
        if target is None:
            return False

        if active.is_shadow(target.uid):
            # Shadow: converge to front position, don't pickup
            Timeline.converge_one(active, target.uid, front_pos)
            self.input_log.append('X')
            self._save_snapshot()
            return True
        else:
            # Solid: normal pickup
            return self.handle_pickup()

    def check_victory(self) -> bool:
        """Check victory conditions"""
        if self.has_branched:
            return False

        preview = self.get_merge_preview()

        # All switches activated
        switches_ok = preview.all_switches_activated()

        # Player on goal
        goal_ok = preview.terrain.get(preview.player.pos) == TerrainType.GOAL

        self.victory = switches_ok and goal_ok
        return self.victory

    def get_interaction_hint(self) -> tuple:
        """Get interaction hint for X key.

        Returns:
            (hint_text, hint_color, target_pos, is_drop)
            hint_text: 'X 拾取' / 'X 放下' / 'X 收束' / ''
            hint_color: (r, g, b) frame color
            target_pos: (x, y) target cell, None if no hint
            is_drop: True if this is a drop hint (use inset frame)
        """
        active = self.get_active_branch()
        px, py = active.player.pos
        dx, dy = active.player.direction
        front_pos = (px + dx, py + dy)

        # If holding, show drop hint (only if can drop)
        if active.get_held_items():
            can_drop = Physics.collision_at(front_pos, active) <= 0
            if can_drop:
                return ('放下', (50, 200, 50), front_pos, True)  # Green, inset
            else:
                return ('', (0, 0, 0), None, False)  # No hint for blocked

        # Cannot pickup while standing on NO_CARRY tile - hide hint
        player_pos = (px, py)
        if Physics.effective_capacity(active, at_pos=player_pos) == 0:
            return ('', (0, 0, 0), None, False)  # No hint in NO_CARRY zone

        # Find grounded box at front position
        target = active.find_box_at(front_pos)

        if target is None:
            return ('', (0, 0, 0), None, False)

        if active.is_shadow(target.uid):
            return ('收束', (0, 220, 220), front_pos, False)  # Cyan
        else:
            return ('拾取', (50, 200, 50), front_pos, False)  # Green

    def get_timeline_hint(self) -> str:
        """Get timeline hint for branch point.

        Returns: 'V' when on branch point (for highlight), '' otherwise
        """
        if self.has_branched:
            #return 'C 合併  Tab 切換視角'
            return 'C 合併'

        active = self.get_active_branch()
        terrain = active.terrain.get(active.player.pos)
        if terrain in self.BRANCH_DECREMENT:
            return 'V 分裂'

        return ''
