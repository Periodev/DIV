# Renderer Refactor Guide — for Codex

## Context

DIV_Godot is a timeline-puzzle game in Godot 4.3.
The renderer (`GameRenderer.gd`, 1455 lines) draws everything via `_draw()` immediate mode.
Architecture is clean MVC: `GameScene` → `PresentationModel` → `GameRenderer`.

**Goal**: Improve iteration speed and code clarity. NOT a rewrite.
**Constraint**: Do NOT change game logic, PresentationModel pipeline, or visual output.

---

## Change 1: @export visual constants

### What
Convert `const` color/size values at the top of `GameRenderer.gd` (lines 11-53) to `@export` vars, so they can be tweaked in Godot Inspector without editing code.

### How
```gdscript
# BEFORE
const NR_FACTOR     := 0.173
const ENTITY_SCALE  := 1.50
const NODE_SCALE    := 1.18
const BORDER_W      := 1.5
const DASH_SCROLL_SPEED := 28.0

# AFTER
@export_group("Entity Sizing")
@export var nr_factor: float = 0.173
@export var entity_scale: float = 1.50
@export var node_scale: float = 1.18

@export_group("Border & Animation")
@export var border_w: float = 1.5
@export var dash_scroll_speed: float = 28.0
```

### Which constants to convert
Convert these (frequently tuned during visual iteration):
- `NR_FACTOR`, `ENTITY_SCALE`, `NODE_SCALE`
- `BORDER_W`, `DASH_SCROLL_SPEED`, `TITLE_MARGIN_BASE`
- `LINE_NORMAL`, `LINE_DASHED`, `LINE_BROKEN`, `LINE_CROSS`, `LINE_STABLE`
- `BOX_COLORS` (make it `@export var box_colors: Array[Color]`)

Do NOT convert (rarely changed, used as identity):
- `COLOR_BG` (must stay pure black)
- `COLOR_FLASH` (semantic constant)
- All `COLOR_HINT_*` constants (these belong to the hint box system, see Change 3)

### Rename convention
`const UPPER_SNAKE` → `@export var lower_snake` (GDScript convention for exported vars).

### References to update
All internal references change from `UPPER_SNAKE` to `lower_snake`. Use find-and-replace per constant. These are only referenced within `GameRenderer.gd` itself — no external callers except:
- `LevelPreview.gd` uses `GameRenderer.branch_marker_dot_positions()` and `GameRenderer.branch_marker_dot_radius()` (static methods around line 904-937). These reference `NR_FACTOR` — update to use a default parameter or class constant if the static methods can't access instance @export vars.

### Static method compatibility
`branch_marker_dot_positions()` and `branch_marker_dot_radius()` are `static` and cannot access instance `@export` vars. Solution: keep a parallel `const _DEFAULT_NR_FACTOR := 0.173` for the static methods only, and use the `@export` var in all instance methods.

---

## Change 2: Cache repeated calculations in draw_frame()

### What
`eff`, `cell_scale`, and `NR` are recalculated in many helper methods. Compute once and store.

### How
Add cached fields:
```gdscript
# Add to State section (around line 58)
var _eff: float = 0.0
var _cell_scale: float = 0.0
var _nr: float = 0.0
var _gpx: float = 0.0
var _alpha: float = 1.0
```

Compute in `_draw()` entry (line 99-106):
```gdscript
func _draw() -> void:
    if _spec == null or _spec.state == null:
        return
    var gs: int = _spec.state.grid_size
    _eff = _spec.cell_size * _spec.scale
    _gpx = _eff * gs
    _alpha = _spec.alpha
    _cell_scale = _eff / 80.0
    _nr = _eff * nr_factor * entity_scale
    # ... rest unchanged
```

Then replace in all helpers:
- `var eff: float = _spec.cell_size * _spec.scale` → use `_eff`
- `var cell_scale: float = eff / 80.0` → use `_cell_scale`
- `var NR: float = eff * NR_FACTOR * ENTITY_SCALE` → use `_nr`
- Remove the local `eff` parameter from helpers where it's only used for these calculations

### Approach
Do NOT remove `eff` parameter from method signatures in one big refactor. Instead:
1. Add the cached vars
2. Set them in `_draw()`
3. Inside each helper, replace `var NR = ...` with `var NR = _nr` (or use `_nr` directly)
4. Gradually remove redundant `eff` parameters in a later pass

This keeps the change incremental and testable.

---

## Change 3: HintLayoutBuilder + optional Control node path

### What
Adaptive hint boxes (Tab, Diverge, Merge, Fetch, Preview) are pure UI rectangles with text.
Currently implemented as 7 methods / ~118 lines in GameRenderer:

```
_draw_adaptive_hints()        13 lines
_draw_tab_switch_hints()      25 lines
_draw_tab_hint_box()          21 lines
_draw_timeline_hint_box()     15 lines
_draw_merge_preview_hint()    14 lines
_draw_merge_hint()            15 lines
_draw_fetch_mode_indicator()  15 lines
```

### Step A — HintLayoutBuilder (prerequisite, do this first)

Create `scripts/HintLayoutBuilder.gd` as a pure-static calculation class (no Node, no draw calls):

```gdscript
class_name HintLayoutBuilder

class HintBoxSpec:
    var visible:      bool
    var text:         String
    var rect:         Rect2    # absolute screen coordinates
    var bg_color:     Color
    var border_color: Color
    var text_color:   Color
    var font_size:    int
    var has_arrow:    bool
    var arrow_dx:     int      # -1 left, +1 right
    var arrow_pos:    Vector2  # absolute screen position

static func build(
        spec: PresentationModel.BranchViewSpec,
        viewport_size: Vector2) -> Array[HintBoxSpec]:
    # Move all condition logic, position formulas, and color mappings here.
    # No draw_rect, no _global_rect_to_local — output is raw Rect2 in screen space.
    # Spec fields consumed:
    #   spec.has_branched, spec.timeline_hint, spec.branch_hint_active,
    #   spec.title (for tab active/inactive),
    #   spec.show_merge_preview_hint, spec.is_merge_preview,
    #   spec.show_merge_hint, spec.merge_hint_enabled,
    #   spec.show_fetch_indicator, spec.fetch_mode_enabled
    var boxes: Array[HintBoxSpec] = []
    # ... build and append one HintBoxSpec per visible hint ...
    return boxes
```

**Line count impact:**
- `HintLayoutBuilder.gd`: +~100 lines (new file)
- `GameRenderer._draw_adaptive_hints()`: 7 methods → 1 method, −106 lines
- **Net: ≈ 0 lines saved** — value is architectural, not quantitative

After Step A, GameRenderer's `_draw_adaptive_hints()` becomes:
```gdscript
func _draw_adaptive_hints(a: float) -> void:
    for box in HintLayoutBuilder.build(_spec, get_viewport_rect().size):
        if not box.visible:
            continue
        var rect := _global_rect_to_local(box.rect)
        var arrow_pos_local := box.arrow_pos - position
        draw_rect(rect, _col(box.bg_color,     a * 0.8))
        draw_rect(rect, _col(box.border_color, a), false, 2.0)
        _draw_text_in_rect(box.text, rect, box.font_size, _col(box.text_color, a))
        if box.has_arrow:
            _draw_arrow(arrow_pos_local, box.arrow_dx, 0, 11, _col(box.text_color, a))
```

### Step B — Control node path (optional, do after Step A)

Only worth doing if you want hint boxes editable in the Godot Inspector.

Target structure:
```
GameRenderer (Node2D)
└── HintBoxContainer (Control)
    ├── TabLeftBox  (PanelContainer + Label)
    ├── TabRightBox (PanelContainer + Label)
    ├── DivergeBox  (PanelContainer + Label)
    ├── MergeBox    (PanelContainer + Label)
    ├── PreviewBox  (PanelContainer + Label)
    └── FetchBox    (PanelContainer + Label)
```

`HintBoxContainer.gd` calls `HintLayoutBuilder.build()` and applies results to node properties
(position, visible, modulate, Label.text, StyleBoxFlat colors) instead of drawing.

In `GameRenderer.draw_frame()`, replace `_draw_adaptive_hints(a)` call with
`$HintBoxContainer.update_hints(_spec)`.

When Step B is enabled, disable the immediate-mode hint draw path in `_draw()`
so hints are rendered by exactly one system (Control nodes only).

**Alpha:** apply via `modulate.a` on HintBoxContainer.
**Position:** same formulas as HintLayoutBuilder.build(), applied as `node.position`.
**Colors:** `StyleBoxFlat` on each PanelContainer, set dynamically from HintBoxSpec.

---

## Change 4: Conditional queue_redraw()

### What
Currently `_process()` (line 89-92) calls `queue_redraw()` every frame unconditionally. Most frames nothing changes.

### How
```gdscript
var _needs_redraw: bool = true   # add to State section

func draw_frame(spec: PresentationModel.BranchViewSpec) -> void:
    _spec = spec
    if spec != null:
        position = Vector2(spec.pos_x, spec.pos_y)
    _needs_redraw = true

func _process(delta: float) -> void:
    _time += delta
    # Always redraw if there are active animations
    if _spec != null:
        var has_animation: bool = (
            _spec.goal_glow > 0 or          # pulsing goal
            _spec.flash_intensity > 0.0 or   # flash fading
            _spec.falling_progress >= 0.0    # falling box
        )
        if _needs_redraw or has_animation:
            queue_redraw()
            _needs_redraw = false
```

### Caveat
The dashed-line scroll animation (`_dash_offset()`) uses `Time.get_ticks_msec()` so it auto-animates. If dashed lines are visible, we need continuous redraw. Add a check:
```gdscript
var has_dashes: bool = _spec.has_branched  # shadow connections are dashed
```
If this makes the optimization too marginal (branches are common), it's fine to skip this change. It's the lowest priority.

---

## DO NOT change

1. **Core `_draw()` structure** — the 6-section dispatch is clean
2. **Entity drawing** (`_draw_box_diamond`, `_draw_overlap_box_diamond`, `_draw_player`) — these must stay in `_draw()` due to dynamic entity counts and overlap logic
3. **Terrain drawing** (`_draw_connections`, `_draw_nodes`) — immediate mode is correct here
4. **PresentationModel.gd** — no changes
5. **GameScene.gd** — no changes except wiring `HintBoxContainer` if Change 3 is done
6. **Visual output** — all changes must produce identical pixels

---

## Priority order

1. **Change 1** (@export) — highest impact on iteration speed, lowest risk
2. **Change 2** (cache calculations) — small code cleanup, no risk
3. **Change 3** (hint box extraction) — medium effort, removes ~130 lines from _draw()
4. **Change 4** (conditional redraw) — lowest priority, marginal benefit

---

## Testing

After each change, verify:
- [ ] Game launches without errors
- [ ] Both renderer panels display correctly (main + sub branch)
- [ ] Merge preview overlay works
- [ ] All hint boxes appear/disappear correctly in branched state
- [ ] Goal glow animation still pulses
- [ ] Falling box animation still morphs
- [ ] Dashed lines still scroll
- [ ] Flash red overlay still works on failed moves
- [ ] LevelPreview (if exists) still renders branch markers correctly
