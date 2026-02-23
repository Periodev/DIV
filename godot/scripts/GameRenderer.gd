# GameRenderer.gd - Godot visual renderer for one branch panel
# Replaces Python's render_arc.py / renderer.py
# Draws using Node2D's _draw() API (immediate-mode style).
extends Node2D
class_name GameRenderer

# ---------------------------------------------------------------------------
# Layout constants (matching Python's presentation_model.py)
# ---------------------------------------------------------------------------
var cell_size: int  = 80   # set by GameScene: TARGET_PANEL / grid_size
const BORDER_W      := 3   # border width in pixels

# Terrain colours
const COLOR_FLOOR     := Color(0.16, 0.16, 0.20)
const COLOR_WALL      := Color(0.10, 0.10, 0.10)
const COLOR_GOAL_OFF  := Color(0.45, 0.38, 0.05)
const COLOR_GOAL_ON   := Color(1.00, 0.85, 0.10)
const COLOR_SWITCH_ON := Color(0.80, 0.80, 0.40)
const COLOR_SWITCH_OFF:= Color(0.40, 0.40, 0.40)
const COLOR_HOLE      := Color(0.05, 0.05, 0.08)
const COLOR_HOLE_FILL := Color(0.30, 0.25, 0.20)
const COLOR_BRANCH    := Color(0.10, 0.40, 0.60)
const COLOR_NO_CARRY  := Color(0.25, 0.10, 0.10)

# Entity colours
const COLOR_PLAYER        := Color(0.25, 0.50, 1.00)
const COLOR_PLAYER_FOCUS  := Color(0.35, 0.65, 1.00)
const COLOR_BOX_NORMAL    := Color(0.70, 0.55, 0.20)
const COLOR_BOX_SHADOW    := Color(0.40, 0.32, 0.12, 0.55)
const COLOR_BOX_HELD      := Color(0.90, 0.75, 0.30)
const COLOR_BOX_OUTLINE   := Color(1.00, 1.00, 1.00, 0.30)

# UI colours
const COLOR_BORDER_FOCUS  := Color(1.00, 0.55, 0.00)   # orange
const COLOR_BORDER_SIDE   := Color(0.00, 0.86, 1.00)   # cyan
const COLOR_HINT_TEXT     := Color(0.90, 0.90, 0.90)
const COLOR_BG            := Color(0.08, 0.08, 0.10)


# ---------------------------------------------------------------------------
# State set by GameScene each frame before queue_redraw()
# ---------------------------------------------------------------------------
var branch_state:    BranchState  = null   # the BranchState to draw
var is_focused:      bool         = true
var border_color:    Color        = COLOR_BORDER_FOCUS
var panel_scale:     float        = 1.0    # 1.0 = full, 0.7 = side panel
var panel_alpha:     float        = 1.0

var goal_active:     bool         = false
var animation_frame: int          = 0      # ticks up each second for blink
var is_merge_preview:bool         = false

# Flash effect
var flash_pos:       Vector2i     = Vector2i(-1, -1)
var flash_intensity: float        = 0.0   # 0.0–1.0

# Falling box progress: {key: float} where key = [uid, pos]
var falling_progress: Dictionary  = {}

# Interaction hint
var hint_text:       String       = ""
var hint_color:      Color        = Color.WHITE
var hint_target_pos: Vector2i     = Vector2i(-1, -1)
var hint_is_drop:    bool         = false

# Title shown above panel
var panel_title:     String       = "MAIN"


# ---------------------------------------------------------------------------
# Draw entry point
# ---------------------------------------------------------------------------

func _draw() -> void:
	if branch_state == null:
		return

	var gs := branch_state.grid_size
	var grid_px := gs * cell_size * panel_scale

	# Background
	draw_rect(Rect2(0, 0, grid_px, grid_px), COLOR_BG)

	# Terrain
	_draw_terrain(gs)

	# Interaction hint highlight
	if hint_target_pos != Vector2i(-1, -1):
		_draw_hint_highlight()

	# Entities
	_draw_entities(gs)

	# Flash overlay
	if flash_intensity > 0.0 and flash_pos != Vector2i(-1, -1):
		_draw_flash()

	# Panel border
	_draw_border(grid_px)

	# Title
	_draw_title()


# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------

func _draw_terrain(gs: int) -> void:
	var blink_on := (animation_frame % 2) == 0

	for y in gs:
		for x in gs:
			var pos := Vector2i(x, y)
			var tt: int = branch_state.terrain.get(pos, Enums.TerrainType.FLOOR)
			var color := _terrain_color(tt, pos, blink_on)
			_draw_cell(x, y, color)

			# Branch point: draw number of uses
			if tt in [Enums.TerrainType.BRANCH1, Enums.TerrainType.BRANCH2,
					  Enums.TerrainType.BRANCH3, Enums.TerrainType.BRANCH4]:
				_draw_branch_uses(x, y, tt)


func _terrain_color(tt: int, pos: Vector2i, blink_on: bool) -> Color:
	match tt:
		Enums.TerrainType.WALL:
			return COLOR_WALL
		Enums.TerrainType.GOAL:
			if goal_active:
				return COLOR_GOAL_ON if blink_on else COLOR_GOAL_OFF
			return COLOR_GOAL_OFF
		Enums.TerrainType.SWITCH:
			return COLOR_SWITCH_ON if branch_state.switch_activated(pos) else COLOR_SWITCH_OFF
		Enums.TerrainType.HOLE:
			return COLOR_HOLE_FILL if branch_state.is_hole_filled(pos) else COLOR_HOLE
		Enums.TerrainType.NO_CARRY:
			return COLOR_NO_CARRY
		Enums.TerrainType.BRANCH1, Enums.TerrainType.BRANCH2, \
		Enums.TerrainType.BRANCH3, Enums.TerrainType.BRANCH4:
			return COLOR_BRANCH
		_:
			return COLOR_FLOOR


func _draw_branch_uses(x: int, y: int, tt: int) -> void:
	var uses_map := {
		Enums.TerrainType.BRANCH1: 1,
		Enums.TerrainType.BRANCH2: 2,
		Enums.TerrainType.BRANCH3: 3,
		Enums.TerrainType.BRANCH4: 4,
	}
	var uses: int = uses_map.get(tt, 0)
	var rect := _cell_rect(x, y)
	# Draw dots representing uses
	var dot_r := 4.0 * panel_scale
	var start_x := rect.position.x + rect.size.x * 0.5 - (uses - 1) * dot_r
	for i in uses:
		draw_circle(
			Vector2(start_x + i * dot_r * 2.0, rect.position.y + rect.size.y - dot_r * 2.0),
			dot_r,
			Color(0.80, 0.90, 1.00)
		)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

func _draw_entities(gs: int) -> void:
	var player := branch_state.get_player()

	# Draw boxes first, then player on top
	for e in branch_state.entities:
		var ent := e as Entity
		if ent.uid == 0:
			continue  # player drawn last
		_draw_box(ent)

	# Draw player
	_draw_player(player)


func _draw_box(ent: Entity) -> void:
	if ent.z == -1:
		return  # underground, invisible (hole filled)

	var pos := ent.pos
	var rect := _cell_rect(pos.x, pos.y)
	var inset := rect.grow(-int(6 * panel_scale))

	var is_held   := ent.z == 1
	var is_shadow := branch_state.is_shadow(ent.uid)

	var color: Color
	if is_held:
		color = COLOR_BOX_HELD
	elif is_shadow:
		color = COLOR_BOX_SHADOW
	else:
		color = COLOR_BOX_NORMAL

	# Apply falling offset if applicable
	var fall_key := [ent.uid, ent.pos]
	var fall_prog: float = falling_progress.get(fall_key, -1.0)
	if fall_prog >= 0.0:
		var fall_offset := fall_prog * cell_size * panel_scale
		inset.position.y += fall_offset

	color.a *= panel_alpha
	draw_rect(inset, color)

	# Outline for shadow
	if is_shadow:
		draw_rect(inset, COLOR_BOX_OUTLINE, false, 2.0 * panel_scale)

	# UID label
	var label_color := Color(0, 0, 0, 0.8 * panel_alpha)
	if panel_scale >= 0.85:
		draw_string(
			ThemeDB.fallback_font,
			inset.position + Vector2(inset.size.x * 0.5 - 6, inset.size.y * 0.5 + 6),
			str(ent.uid),
			HORIZONTAL_ALIGNMENT_CENTER,
			-1,
			int(14 * panel_scale),
			label_color
		)


func _draw_player(player: Entity) -> void:
	var rect   := _cell_rect(player.pos.x, player.pos.y)
	var center := rect.get_center()
	var radius := (cell_size * panel_scale * 0.35)

	var col := COLOR_PLAYER_FOCUS if is_focused else COLOR_PLAYER
	col.a   *= panel_alpha
	draw_circle(center, radius, col)

	# Direction arrow
	var dx := float(player.direction.x)
	var dy := float(player.direction.y)
	var tip := center + Vector2(dx, dy) * radius
	draw_line(center, tip, Color(0, 0, 0, 0.8 * panel_alpha), 3.0 * panel_scale, true)


# ---------------------------------------------------------------------------
# Interaction hint highlight
# ---------------------------------------------------------------------------

func _draw_hint_highlight() -> void:
	var rect := _cell_rect(hint_target_pos.x, hint_target_pos.y)
	var c    := hint_color
	c.a      = 0.3 * panel_alpha
	draw_rect(rect, c)
	draw_rect(rect, hint_color, false, 2.0 * panel_scale)


# ---------------------------------------------------------------------------
# Flash effect
# ---------------------------------------------------------------------------

func _draw_flash() -> void:
	var rect := _cell_rect(flash_pos.x, flash_pos.y)
	var c    := Color(1.0, 0.3, 0.3, flash_intensity * panel_alpha)
	draw_rect(rect, c)


# ---------------------------------------------------------------------------
# Panel border
# ---------------------------------------------------------------------------

func _draw_border(grid_px: float) -> void:
	var c := border_color
	c.a  *= panel_alpha
	draw_rect(Rect2(0, 0, grid_px, grid_px), c, false, BORDER_W * panel_scale)


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

func _draw_title() -> void:
	var gs      := branch_state.grid_size
	var grid_px := gs * cell_size * panel_scale
	var c       := Color(1, 1, 1, 0.8 * panel_alpha)
	draw_string(
		ThemeDB.fallback_font,
		Vector2(grid_px * 0.5, -8),
		panel_title,
		HORIZONTAL_ALIGNMENT_CENTER,
		-1,
		int(16 * panel_scale),
		c
	)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

func _cell_rect(x: int, y: int) -> Rect2:
	var s   := cell_size * panel_scale
	return Rect2(x * s + 1, y * s + 1, s - 2, s - 2)


func _draw_cell(x: int, y: int, color: Color) -> void:
	var s   := cell_size * panel_scale
	var c   := color
	c.a    *= panel_alpha
	draw_rect(Rect2(x * s, y * s, s, s), c)
