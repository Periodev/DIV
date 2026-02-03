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


@dataclass
class FrameViewSpec:
    """Complete visual specification for one frame."""
    # Branch panels
    main_branch: BranchViewSpec
    merge_preview: BranchViewSpec
    sub_branch: Optional[BranchViewSpec]

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

    @staticmethod
    def build(controller, animation_frame: int) -> FrameViewSpec:
        """
        Main entry point: build complete frame specification.

        Args:
            controller: GameController instance
            animation_frame: Current animation frame counter

        Returns:
            FrameViewSpec describing what to render
        """
        # Get preview state for goal_active calculation
        preview = controller.get_merge_preview()
        goal_active = ViewModelBuilder._check_goal_active(preview)

        # Get hints (only for focused branch)
        timeline_hint = controller.get_timeline_hint()
        interaction_hint = ViewModelBuilder._extract_interaction_hint(controller)

        # Build main branch spec
        main_spec = ViewModelBuilder._build_branch_spec(
            state=controller.main_branch,
            is_focused=(controller.current_focus == 0),
            title="DIV 0",
            border_color=(0, 100, 200),
            timeline_hint=timeline_hint if controller.current_focus == 0 else '',
            interaction_hint=interaction_hint if controller.current_focus == 0 else None,
            is_merge_preview=False
        )

        # Build merge preview spec (never focused, no hints)
        preview_spec = ViewModelBuilder._build_branch_spec(
            state=preview,
            is_focused=False,
            title="Merge Preview",
            border_color=(150, 50, 150),
            timeline_hint='',
            interaction_hint=None,
            is_merge_preview=True
        )

        # Build sub branch spec (if exists)
        sub_spec = None
        if controller.sub_branch:
            sub_spec = ViewModelBuilder._build_branch_spec(
                state=controller.sub_branch,
                is_focused=(controller.current_focus == 1),
                title="DIV 1",
                border_color=(50, 150, 200),
                timeline_hint=timeline_hint if controller.current_focus == 1 else '',
                interaction_hint=interaction_hint if controller.current_focus == 1 else None,
                is_merge_preview=False
            )

        return FrameViewSpec(
            main_branch=main_spec,
            merge_preview=preview_spec,
            sub_branch=sub_spec,
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
        is_merge_preview: bool
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
            is_merge_preview=is_merge_preview
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
