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
    text: str
    color: Tuple[int, int, int]
    target_pos: Position
    is_inset: bool


@dataclass
class BranchViewSpec:
    """Visual specification for a single branch panel."""
    state: BranchState
    title: str
    is_focused: bool
    border_color: Tuple[int, int, int]
    interaction_hint: Optional[InteractionHint]
    timeline_hint: str
    highlight_branch_point: bool
    is_merge_preview: bool
    show_inherit_hint: bool
    scale: float = 1.0
    pos_x: int = 0
    pos_y: int = 0
    alpha: float = 1.0  # For fade effects during animation


@dataclass
class FrameViewSpec:
    """Complete visual specification for one frame.

    Layout:
    - Single focused branch centered
    - After branching: other branch slides in from right
    - Tab triggers slide animation
    """
    # Main branches (positioned based on focus and animation)
    main_branch: BranchViewSpec      # DIV 0
    sub_branch: Optional[BranchViewSpec]  # DIV 1

    # Animation state
    slide_progress: float  # 0.0 = no animation, 0.0->1.0 = animating
    slide_direction: int   # 1 = focus moving right (0->1), -1 = focus moving left (1->0)

    # Global state
    goal_active: bool
    has_branched: bool
    animation_frame: int
    current_focus: int

    # Game end states
    is_collapsed: bool
    is_victory: bool

    # Debug info
    step_count: int
    input_sequence: List[str]


class ViewModelBuilder:
    """Transforms game state into visual specifications."""

    BRANCH_TERRAINS = {
        TerrainType.BRANCH1, TerrainType.BRANCH2,
        TerrainType.BRANCH3, TerrainType.BRANCH4
    }

    # === Layout Constants ===
    WINDOW_WIDTH = 1150
    WINDOW_HEIGHT = 600

    PADDING = 30
    CELL_SIZE = 75
    GRID_SIZE = 6
    GRID_PX = CELL_SIZE * GRID_SIZE  # 450
    GAP = 30

    # Scale settings
    FOCUS_SCALE = 1.0      # Focused branch: full size
    SIDE_SCALE = 0.7       # Non-focused branch: 70% size (315px)
    SIDE_GRID_PX = int(GRID_PX * SIDE_SCALE)  # 315

    # Focused branch: always centered
    CENTER_X = (WINDOW_WIDTH - GRID_PX) // 2  # 350
    CENTER_Y = (WINDOW_HEIGHT - GRID_PX) // 2  # 75

    # Side positions (for non-focused branch at 0.7 scale)
    RIGHT_X = CENTER_X + GRID_PX + GAP  # 830 (to the right of focused)
    LEFT_X = CENTER_X - GAP - SIDE_GRID_PX  # 5 (to the left of focused)

    # Vertical center for side branch (adjusted for smaller size)
    SIDE_CENTER_Y = (WINDOW_HEIGHT - SIDE_GRID_PX) // 2  # 142

    @staticmethod
    def build(controller, animation_frame: int,
              slide_progress: float = 0.0,
              slide_direction: int = 0,
              merge_preview_active: bool = False,
              show_inherit_hint: bool = False,
              merge_preview_progress: float = 0.0,
              merge_preview_swap_progress: float = 0.0,
              merge_animation_progress: float = 0.0,
              merge_animation_pre_focus: int = None,
              merge_animation_stored_main = None,
              merge_animation_stored_sub = None) -> FrameViewSpec:
        """Build frame specification with slide animation and merge preview support."""
        B = ViewModelBuilder

        # Get hints
        timeline_hint = controller.get_timeline_hint()
        interaction_hint = B._extract_interaction_hint(controller)

        # Goal active check
        preview = controller.get_merge_preview()
        goal_active = B._check_goal_active(preview)

        focus = controller.current_focus
        has_branched = controller.has_branched

        # Special case: merge animation playing (use stored states for visual animation)
        if merge_animation_progress > 0 and merge_animation_stored_main and merge_animation_stored_sub:
            # Override controller states with stored pre-merge states
            main_branch_state = merge_animation_stored_main
            sub_branch_state = merge_animation_stored_sub
            has_branched = True
            focus = merge_animation_pre_focus
            merge_preview_active = True
        else:
            # Use normal controller states
            main_branch_state = controller.main_branch
            sub_branch_state = controller.sub_branch

        # Alpha values (for merge preview)
        main_alpha = 1.0
        sub_alpha = 1.0
        is_merge_preview = merge_preview_active or merge_preview_progress > 0 or merge_animation_progress > 0

        # Calculate positions and scales based on animation state
        if not has_branched:
            # Single branch, centered at full scale
            main_x, main_y, main_scale = B.CENTER_X, B.CENTER_Y, B.FOCUS_SCALE
            sub_x, sub_y, sub_scale = B.WINDOW_WIDTH + 50, B.CENTER_Y, B.SIDE_SCALE
        elif merge_preview_active or merge_preview_progress > 0:
            # Merge preview mode: both branches move to center, non-focused becomes transparent
            main_x, main_y, main_scale, sub_x, sub_y, sub_scale, main_alpha, sub_alpha = B._calc_merge_preview_positions(
                focus, merge_preview_progress, merge_preview_active
            )
            # If swapping focus in preview, animate position and alpha swap
            if merge_preview_swap_progress > 0:
                main_x, main_y, sub_x, sub_y, main_alpha, sub_alpha = B._calc_merge_preview_swap(
                    focus, merge_preview_swap_progress, main_x, main_y, sub_x, sub_y, main_alpha, sub_alpha
                )
            # If merging, animate non-focused to center and fade in
            if merge_animation_progress > 0:
                main_x, main_y, sub_x, sub_y, main_alpha, sub_alpha = B._calc_merge_animation(
                    focus, merge_animation_progress, main_x, main_y, sub_x, sub_y, main_alpha, sub_alpha
                )
        else:
            # Two branches - focused centered (large), other on side (small)
            if slide_progress > 0:
                # Animating: interpolate position, scale, and Y
                main_x, main_y, main_scale, sub_x, sub_y, sub_scale = B._calc_slide_positions(
                    focus, slide_progress, slide_direction
                )
            else:
                # Static positions
                if focus == 0:
                    main_x, main_y, main_scale = B.CENTER_X, B.CENTER_Y, B.FOCUS_SCALE
                    sub_x, sub_y, sub_scale = B.RIGHT_X, B.SIDE_CENTER_Y, B.SIDE_SCALE
                else:
                    main_x, main_y, main_scale = B.LEFT_X, B.SIDE_CENTER_Y, B.SIDE_SCALE
                    sub_x, sub_y, sub_scale = B.CENTER_X, B.CENTER_Y, B.FOCUS_SCALE

        # Build main branch spec (DIV 0)
        main_spec = B._build_branch_spec(
            state=main_branch_state,
            is_focused=(focus == 0),
            title="DIV 0" if has_branched else "MAIN",
            border_color=(255, 140, 0),  # Orange - high contrast
            timeline_hint=timeline_hint if focus == 0 else '',
            interaction_hint=interaction_hint if focus == 0 else None,
            is_merge_preview=is_merge_preview,
            show_inherit_hint=show_inherit_hint and focus == 0,
            has_branched=has_branched,
            scale=main_scale,
            pos_x=main_x,
            pos_y=main_y,
            alpha=main_alpha
        )

        # Build sub branch spec (DIV 1)
        sub_spec = None
        if sub_branch_state:
            sub_spec = B._build_branch_spec(
                state=sub_branch_state,
                is_focused=(focus == 1),
                title="DIV 1",
                border_color=(0, 220, 255),  # Cyan - high contrast
                timeline_hint=timeline_hint if focus == 1 else '',
                interaction_hint=interaction_hint if focus == 1 else None,
                is_merge_preview=is_merge_preview,
                show_inherit_hint=show_inherit_hint and focus == 1,
                has_branched=has_branched,
                scale=sub_scale,
                pos_x=sub_x,
                pos_y=sub_y,
                alpha=sub_alpha
            )

        return FrameViewSpec(
            main_branch=main_spec,
            sub_branch=sub_spec,
            slide_progress=slide_progress,
            slide_direction=slide_direction,
            goal_active=goal_active,
            has_branched=has_branched,
            animation_frame=animation_frame,
            current_focus=focus,
            is_collapsed=controller.collapsed,
            is_victory=controller.victory,
            step_count=len(controller.history) - 1,
            input_sequence=controller.input_log
        )

    @staticmethod
    def _calc_slide_positions(focus: int, progress: float, direction: int):
        """Calculate branch positions, scales, and Y during slide animation.

        Returns: (main_x, main_y, main_scale, sub_x, sub_y, sub_scale)
        direction: 1 = switching from 0 to 1, -1 = switching from 1 to 0
        """
        B = ViewModelBuilder
        t = B._ease_in_out(progress)

        def lerp(a, b, t):
            return a + (b - a) * t

        if direction == 1:  # Focus 0 -> 1: DIV0 shrinks to left, DIV1 grows to center
            # DIV 0: center -> left, large -> small
            main_x = int(lerp(B.CENTER_X, B.LEFT_X, t))
            main_y = int(lerp(B.CENTER_Y, B.SIDE_CENTER_Y, t))
            main_scale = lerp(B.FOCUS_SCALE, B.SIDE_SCALE, t)
            # DIV 1: right -> center, small -> large
            sub_x = int(lerp(B.RIGHT_X, B.CENTER_X, t))
            sub_y = int(lerp(B.SIDE_CENTER_Y, B.CENTER_Y, t))
            sub_scale = lerp(B.SIDE_SCALE, B.FOCUS_SCALE, t)
        else:  # Focus 1 -> 0: DIV1 shrinks to right, DIV0 grows to center
            # DIV 0: left -> center, small -> large
            main_x = int(lerp(B.LEFT_X, B.CENTER_X, t))
            main_y = int(lerp(B.SIDE_CENTER_Y, B.CENTER_Y, t))
            main_scale = lerp(B.SIDE_SCALE, B.FOCUS_SCALE, t)
            # DIV 1: center -> right, large -> small
            sub_x = int(lerp(B.CENTER_X, B.RIGHT_X, t))
            sub_y = int(lerp(B.CENTER_Y, B.SIDE_CENTER_Y, t))
            sub_scale = lerp(B.FOCUS_SCALE, B.SIDE_SCALE, t)

        return main_x, main_y, main_scale, sub_x, sub_y, sub_scale

    @staticmethod
    def _ease_in_out(t: float) -> float:
        """Smooth ease-in-out curve."""
        if t < 0.5:
            return 2 * t * t
        return 1 - (-2 * t + 2) ** 2 / 2

    @staticmethod
    def _calc_merge_preview_positions(focus: int, progress: float, is_active: bool):
        """Calculate positions for merge preview mode.

        Returns: (main_x, main_y, main_scale, sub_x, sub_y, sub_scale, main_alpha, sub_alpha)
        In preview: non-focused moves to center, becomes transparent, with diagonal offset
        """
        B = ViewModelBuilder
        t = B._ease_in_out(progress) if progress < 1.0 else 1.0

        def lerp(a, b, t):
            return a + (b - a) * t

        # Diagonal offset for visual separation (bottom-right)
        OFFSET_X = 2
        OFFSET_Y = 2

        # Determine starting positions based on focus
        if focus == 0:
            # DIV 0 focused: stays at center, DIV 1 animates from right to center with offset
            main_x, main_y, main_scale = B.CENTER_X, B.CENTER_Y, B.FOCUS_SCALE
            main_alpha = 1.0

            # DIV 1: animate from right side position to center + offset
            start_x, start_y = B.RIGHT_X, B.SIDE_CENTER_Y
            start_scale = B.SIDE_SCALE
            target_x = B.CENTER_X + OFFSET_X
            target_y = B.CENTER_Y + OFFSET_Y
            sub_x = int(lerp(start_x, target_x, t))
            sub_y = int(lerp(start_y, target_y, t))
            sub_scale = lerp(start_scale, B.FOCUS_SCALE, t)
            sub_alpha = lerp(1.0, 0.7, t)  # Fade to 70% opaque (more visible)
        else:
            # DIV 1 focused: stays at center, DIV 0 animates from left to center with offset
            sub_x, sub_y, sub_scale = B.CENTER_X, B.CENTER_Y, B.FOCUS_SCALE
            sub_alpha = 1.0

            # DIV 0: animate from left side position to center + offset
            start_x, start_y = B.LEFT_X, B.SIDE_CENTER_Y
            start_scale = B.SIDE_SCALE
            target_x = B.CENTER_X + OFFSET_X
            target_y = B.CENTER_Y + OFFSET_Y
            main_x = int(lerp(start_x, target_x, t))
            main_y = int(lerp(start_y, target_y, t))
            main_scale = lerp(start_scale, B.FOCUS_SCALE, t)
            main_alpha = lerp(1.0, 0.7, t)  # Fade to 70% opaque (more visible)

        return main_x, main_y, main_scale, sub_x, sub_y, sub_scale, main_alpha, sub_alpha

    @staticmethod
    def _calc_merge_preview_swap(focus: int, progress: float,
                                   main_x: int, main_y: int, sub_x: int, sub_y: int,
                                   main_alpha: float, sub_alpha: float):
        """Calculate positions during merge preview focus swap.

        Returns: (main_x, main_y, sub_x, sub_y, main_alpha, sub_alpha)
        Swaps positions between center and offset. Alpha values remain constant
        during animation to avoid white flash, then snap to correct values when focus switches.
        """
        B = ViewModelBuilder
        t = B._ease_in_out(progress)

        def lerp(a, b, t):
            return a + (b - a) * t

        # Diagonal offset
        OFFSET_X = 2
        OFFSET_Y = 2

        if focus == 0:
            # Currently DIV 0 focused: swap positions only
            # DIV 0: center → offset (alpha stays 1.0)
            main_x = int(lerp(B.CENTER_X, B.CENTER_X + OFFSET_X, t))
            main_y = int(lerp(B.CENTER_Y, B.CENTER_Y + OFFSET_Y, t))
            # DIV 1: offset → center (alpha stays 0.7)
            sub_x = int(lerp(B.CENTER_X + OFFSET_X, B.CENTER_X, t))
            sub_y = int(lerp(B.CENTER_Y + OFFSET_Y, B.CENTER_Y, t))
        else:
            # Currently DIV 1 focused: swap positions only
            # DIV 0: offset → center (alpha stays 0.7)
            main_x = int(lerp(B.CENTER_X + OFFSET_X, B.CENTER_X, t))
            main_y = int(lerp(B.CENTER_Y + OFFSET_Y, B.CENTER_Y, t))
            # DIV 1: center → offset (alpha stays 1.0)
            sub_x = int(lerp(B.CENTER_X, B.CENTER_X + OFFSET_X, t))
            sub_y = int(lerp(B.CENTER_Y, B.CENTER_Y + OFFSET_Y, t))

        # Alpha values unchanged during animation
        return main_x, main_y, sub_x, sub_y, main_alpha, sub_alpha

    @staticmethod
    def _calc_merge_animation(focus: int, progress: float,
                               main_x: int, main_y: int, sub_x: int, sub_y: int,
                               main_alpha: float, sub_alpha: float):
        """Calculate positions and alphas during merge animation.

        Returns: (main_x, main_y, sub_x, sub_y, main_alpha, sub_alpha)
        Non-focused branch moves from offset to exact center (full overlap)
        and becomes opaque (alpha 0.7 → 1.0) to visually merge.
        """
        B = ViewModelBuilder
        t = B._ease_in_out(progress)

        def lerp(a, b, t):
            return a + (b - a) * t

        # Diagonal offset
        OFFSET_X = 2
        OFFSET_Y = 2

        if focus == 0:
            # DIV 0 focused: DIV 1 moves from offset to center and fades in
            # DIV 0: stays at center (alpha 1.0)
            # DIV 1: offset → center, alpha 0.7 → 1.0
            sub_x = int(lerp(B.CENTER_X + OFFSET_X, B.CENTER_X, t))
            sub_y = int(lerp(B.CENTER_Y + OFFSET_Y, B.CENTER_Y, t))
            sub_alpha = lerp(0.7, 1.0, t)
        else:
            # DIV 1 focused: DIV 0 moves from offset to center and fades in
            # DIV 1: stays at center (alpha 1.0)
            # DIV 0: offset → center, alpha 0.7 → 1.0
            main_x = int(lerp(B.CENTER_X + OFFSET_X, B.CENTER_X, t))
            main_y = int(lerp(B.CENTER_Y + OFFSET_Y, B.CENTER_Y, t))
            main_alpha = lerp(0.7, 1.0, t)

        return main_x, main_y, sub_x, sub_y, main_alpha, sub_alpha

    @staticmethod
    def _build_branch_spec(
        state: BranchState,
        is_focused: bool,
        title: str,
        border_color: Tuple[int, int, int],
        timeline_hint: str,
        interaction_hint: Optional[InteractionHint],
        is_merge_preview: bool,
        show_inherit_hint: bool,
        has_branched: bool,
        scale: float = 1.0,
        pos_x: int = 0,
        pos_y: int = 0,
        alpha: float = 1.0
    ) -> BranchViewSpec:
        """Build visual spec for a single branch."""
        highlight = ViewModelBuilder._is_on_branch_point(state) and not has_branched

        return BranchViewSpec(
            state=state,
            title=title,
            is_focused=is_focused,
            border_color=border_color,
            interaction_hint=interaction_hint,
            timeline_hint=timeline_hint,
            highlight_branch_point=highlight and is_focused,
            is_merge_preview=is_merge_preview,
            show_inherit_hint=show_inherit_hint,
            scale=scale,
            pos_x=pos_x,
            pos_y=pos_y,
            alpha=alpha
        )

    @staticmethod
    def _check_goal_active(state: BranchState) -> bool:
        """Check if all switches are activated by boxes."""
        return all(
            state.switch_activated(pos)
            for pos, t in state.terrain.items()
            if t == TerrainType.SWITCH
        )

    @staticmethod
    def _extract_interaction_hint(controller) -> Optional[InteractionHint]:
        """Convert controller hint tuple to InteractionHint dataclass."""
        raw = controller.get_interaction_hint()
        text, color, pos, is_inset = raw
        if not text:
            return None
        return InteractionHint(text=text, color=color, target_pos=pos, is_inset=is_inset)

    @staticmethod
    def _is_on_branch_point(state: BranchState) -> bool:
        """Check if player is standing on a branch terrain."""
        player_pos = state.player.pos
        terrain = state.terrain.get(player_pos)
        return terrain in ViewModelBuilder.BRANCH_TERRAINS
