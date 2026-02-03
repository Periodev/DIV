# presentation_model.py - Presentation Model Layer (Layer 2)
#
# Transforms game state into visual specifications.
# This layer decides WHAT to display, not HOW to display it.

from dataclasses import dataclass
from typing import Optional, Tuple, List
from timeline_system import BranchState, TerrainType, Position


@dataclass
class InteractionHint:
    """Describes an interaction hint to display on a cell."""
    text: str                      # "拾取" / "放下" / "收束"
    color: Tuple[int, int, int]    # RGB frame color
    target_pos: Position           # Grid position to show hint
    is_inset: bool                 # True = smaller inset frame (for drop)


@dataclass
class BranchViewSpec:
    """Visual specification for a single branch panel."""
    state: BranchState             # Game state reference
    title: str                     # "DIV 0", "DIV 1", "Merge Preview"
    is_focused: bool               # Is this the active branch?
    border_color: Tuple[int, int, int]
    interaction_hint: Optional[InteractionHint]  # Cell hint (focused only)
    timeline_hint: str             # "V 分裂" / "C 合併" / ""
    highlight_branch_point: bool   # Player standing on branch terrain
    is_merge_preview: bool         # Special rendering mode
    scale: float = 1.0             # Scale factor (1.0 = 75px cells, 0.73 = 55px)
    pos_x: int = 0                 # Panel X position
    pos_y: int = 0                 # Panel Y position


@dataclass
class TutorialSpec:
    """Tutorial box specification."""
    title: str
    items: List[str]
    visible: bool = True


@dataclass
class FrameViewSpec:
    """Complete visual specification for one frame."""
    # Branch panels
    main_branch: BranchViewSpec
    merge_preview: BranchViewSpec
    sub_branch: Optional[BranchViewSpec]

    # Tutorial
    tutorial: Optional[TutorialSpec]

    # Global state
    goal_active: bool
    has_branched: bool
    animation_frame: int

    # Game end states
    is_collapsed: bool
    is_victory: bool

    # For inherited hold hint rendering (merge preview needs these)
    hidden_main: Optional[BranchState]
    hidden_sub: Optional[BranchState]
    current_focus: int

    # Debug info
    step_count: int
    input_sequence: List[str]


class ViewModelBuilder:
    """Transforms game state into visual specifications."""

    # Branch point terrain types
    BRANCH_TERRAINS = {
        TerrainType.BRANCH1, TerrainType.BRANCH2,
        TerrainType.BRANCH3, TerrainType.BRANCH4
    }

    # Layout constants (matching demo.html)
    PADDING = 30
    CELL_SIZE = 75
    GRID_SIZE = 6
    GRID_WIDTH = CELL_SIZE * GRID_SIZE  # 450
    PREVIEW_SCALE = 0.80  # 55px / 75px
    PREVIEW_CELL = int(CELL_SIZE * PREVIEW_SCALE)  # 55px
    PREVIEW_GRID_WIDTH = PREVIEW_CELL * GRID_SIZE  # 330

    @staticmethod
    def build(controller, animation_frame: int,
              tutorial_title: str = None, tutorial_items: List[str] = None) -> FrameViewSpec:
        """
        Main entry point: build complete frame specification.

        Args:
            controller: GameController instance
            animation_frame: Current animation frame counter
            tutorial_title: Optional tutorial box title
            tutorial_items: Optional list of tutorial text items

        Returns:
            FrameViewSpec describing what to render
        """
        B = ViewModelBuilder  # Shorthand

        # Get preview state for goal_active calculation
        preview = controller.get_merge_preview()
        goal_active = B._check_goal_active(preview)

        # Get hints (only for focused branch)
        timeline_hint = controller.get_timeline_hint()
        interaction_hint = B._extract_interaction_hint(controller)

        # Layout positions for 1280x800
        # Left column: Tutorial (top) + Preview (below)
        # Right side: DIV 0 + DIV 1 (scaled to 0.9 to fit)

        # Preview: below tutorial (scale 0.73)
        preview_x = B.PADDING
        preview_y = 380

        # Main grids
        main_scale = 1.0
        main_cell = int(B.CELL_SIZE * main_scale)  
        main_grid_width = main_cell * B.GRID_SIZE  
        grid_gap = 30

        # Position: right-aligned with padding
        main_x = 450
        main_y = B.PADDING + 250
        sub_x = main_x + main_grid_width + grid_gap  

        # Build main branch spec (scaled to fit)
        main_spec = B._build_branch_spec(
            state=controller.main_branch,
            is_focused=(controller.current_focus == 0),
            title="DIV 0",
            border_color=(0, 100, 200),
            timeline_hint=timeline_hint if controller.current_focus == 0 else '',
            interaction_hint=interaction_hint if controller.current_focus == 0 else None,
            is_merge_preview=False,
            scale=main_scale,
            pos_x=main_x,
            pos_y=main_y
        )

        # Build merge preview spec (scaled, bottom-left)
        preview_spec = B._build_branch_spec(
            state=preview,
            is_focused=False,
            title="Merge Preview",
            border_color=(150, 50, 150),
            timeline_hint='',
            interaction_hint=None,
            is_merge_preview=True,
            scale=B.PREVIEW_SCALE,
            pos_x=preview_x,
            pos_y=preview_y
        )

        # Build sub branch spec (if exists, scaled to fit)
        sub_spec = None
        if controller.sub_branch:
            sub_spec = B._build_branch_spec(
                state=controller.sub_branch,
                is_focused=(controller.current_focus == 1),
                title="DIV 1",
                border_color=(50, 150, 200),
                timeline_hint=timeline_hint if controller.current_focus == 1 else '',
                interaction_hint=interaction_hint if controller.current_focus == 1 else None,
                is_merge_preview=False,
                scale=main_scale,
                pos_x=sub_x,
                pos_y=main_y
            )

        # Tutorial spec
        tutorial = None
        if tutorial_items:
            tutorial = TutorialSpec(
                title=tutorial_title or "Tutorial",
                items=tutorial_items,
                visible=True
            )

        return FrameViewSpec(
            main_branch=main_spec,
            merge_preview=preview_spec,
            sub_branch=sub_spec,
            tutorial=tutorial,
            goal_active=goal_active,
            has_branched=controller.has_branched,
            animation_frame=animation_frame,
            is_collapsed=controller.collapsed,
            is_victory=controller.victory,
            hidden_main=controller.main_branch,
            hidden_sub=controller.sub_branch,
            current_focus=controller.current_focus,
            step_count=len(controller.history) - 1,
            input_sequence=controller.input_log
        )

    @staticmethod
    def _build_branch_spec(
        state: BranchState,
        is_focused: bool,
        title: str,
        border_color: Tuple[int, int, int],
        timeline_hint: str,
        interaction_hint: Optional[InteractionHint],
        is_merge_preview: bool,
        scale: float = 1.0,
        pos_x: int = 0,
        pos_y: int = 0
    ) -> BranchViewSpec:
        """Build visual spec for a single branch."""
        # Check if player standing on branch point
        highlight = ViewModelBuilder._is_on_branch_point(state)

        return BranchViewSpec(
            state=state,
            title=title,
            is_focused=is_focused,
            border_color=border_color,
            interaction_hint=interaction_hint,
            timeline_hint=timeline_hint,
            highlight_branch_point=highlight and is_focused,
            is_merge_preview=is_merge_preview,
            scale=scale,
            pos_x=pos_x,
            pos_y=pos_y
        )

    @staticmethod
    def _check_goal_active(state: BranchState) -> bool:
        """Check if all switches have weight (goal should flash)."""
        return all(
            any(e.pos == pos for e in state.entities)
            for pos, t in state.terrain.items()
            if t == TerrainType.SWITCH
        )

    @staticmethod
    def _extract_interaction_hint(controller) -> Optional[InteractionHint]:
        """Convert controller hint tuple to InteractionHint dataclass."""
        raw = controller.get_interaction_hint()
        text, color, pos, is_inset = raw

        if not text:  # Empty hint
            return None

        return InteractionHint(
            text=text,
            color=color,
            target_pos=pos,
            is_inset=is_inset
        )

    @staticmethod
    def _is_on_branch_point(state: BranchState) -> bool:
        """Check if player is standing on a branch terrain."""
        player_pos = state.player.pos
        terrain = state.terrain.get(player_pos)
        return terrain in ViewModelBuilder.BRANCH_TERRAINS
